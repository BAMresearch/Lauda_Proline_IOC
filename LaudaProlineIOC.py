import asyncio
import logging
import socket
import sys
import attrs
from datetime import datetime, timezone
from caproto.server import PVGroup, pvproperty, PvpropertyString, run, template_arg_parser, AsyncLibraryLayer
from caproto import ChannelData

logger = logging.getLogger("LaudaProlineIOC")
logger.setLevel(logging.INFO)

# Validators for IP and Port
def validate_ip_address(instance, attribute, value):
    try:
        socket.inet_aton(value)
    except socket.error:
        raise ValueError(f"Invalid IP address: {value}")


def validate_port_number(instance, attribute, value):
    if not (0 <= value <= 65535):
        raise ValueError(f"Port number must be between 0 and 65535, got {value}")


# LaudaClient encapsulates connection logic
class LaudaClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def _connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        return sock

    async def async_read(self, group_command: str) -> float:
        return await asyncio.to_thread(self.read, group_command)

    def read(self, group_command: str) -> float:
        message = f"{group_command}\r\n"
        with self._connect() as sock:
            sock.sendall(message.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8')
        logging.warn(f"Sent message: {message}, response: {response}")
        if response.startswith("ERR_"):
            logging.error(f"Error reading {group_command}: {response}")
            raise ValueError(f"{response}")
        return float(response.strip())

    def write(self, group_command: str, value: int | float | str | None):
        # group_command like "OUT_SP_00", value like "23.56"
        # if isinstance(value, str):
        #     value = 1 if value.lower() in {'on', 'true'}
        #     value = 0 if value.lower() in {'off', 'false'}
        if value is not None:
            message = f"{group_command}_{value}\r\n"
        else:
            message = f"{group_command}\r\n"
        with self._connect() as sock:
            sock.sendall(message.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8')
        logging.warn(f"Sent message: {message}, response: {response}")
        if not response.startswith("OK"):
            raise ValueError(f"Unexpected response: {response}")


@attrs.define
class LaudaIOC(PVGroup):
    host: str = attrs.field(default="172.17.1.14", validator=validate_ip_address, converter=str)
    port: int = attrs.field(default=4014, validator=validate_port_number, converter=int)
    client: LaudaClient = attrs.field(init=False)
    _communication_lock: asyncio.Lock = attrs.field(init=False, validator=attrs.validators.instance_of(asyncio.Lock))

    def __init__(self, *args, **kwargs) -> None:
        for k in list(kwargs.keys()):
            if k in ['host', 'port']:
                setattr(self, k, kwargs.pop(k))
        self.client = LaudaClient(self.host, self.port)
        super().__init__(*args, **kwargs)
        self._communication_lock = asyncio.Lock()


    TSET = pvproperty(name="TSET", doc="Temperature setpoint", dtype=float, record='ai')
    TSET_RBV = pvproperty(name="TSET_RBV", doc="Setpoint RBV", dtype=float, record='ai')
    @TSET.putter
    async def TSET(self, instance, value: float):
        self.client.write("OUT_SP_00", value)
    @TSET.scan(period=15, use_scan_field=True)
    async def TSET(self, instance: ChannelData, async_lib: AsyncLibraryLayer):
        async with self._communication_lock:
            await self.TSET_RBV.write(self.client.read("IN_SP_00"))

    T_RBV = pvproperty(name="T_RBV", doc="Bath temperature", dtype=float, record='ai')
    @T_RBV.scan(period=15, use_scan_field=True)
    async def T_RBV(self, instance: ChannelData, async_lib: AsyncLibraryLayer):
        async with self._communication_lock:
            await self.T_RBV.write(self.client.read("IN_PV_00"))

    # Start/Stop
    Run = pvproperty(name="Run", doc="Set the chiller to operating mode", dtype=bool, record='bi')
    Run_RBV = pvproperty(name="Run_RBV", doc="Readback for operating mode", dtype=bool, record='bi')
    @Run.putter
    async def Run(self, instance, value: bool):
        print('Run', value)
        if isinstance(value, str):
            value = 1 if value.lower() in {'on', 'true'}
            value = 0 if value.lower() in {'off', 'false'}
        if bool(value):
            self.client.write("START", None)
        else:
            self.client.write("STOP", None)
    @Run.scan(period=15, use_scan_field=True)
    async def Run(self, instance: ChannelData, async_lib: AsyncLibraryLayer):
        async with self._communication_lock:
            # value is inverted: 1 = device is off. Does not seem to be linked to start/stop
            await self.Run_RBV.write(not(bool(float(self.client.read("IN_MODE_02")))))

    # Program selection
    RMP = pvproperty(name="RMP", doc="Set run program (1-5)", dtype=float, record='ai')
    RMP_RBV = pvproperty(name="RMP_RBV", doc="Readback currently running program", dtype=float, record='ai')
    @RMP.putter
    async def RMP(self, instance, value: int):
        if not (1 <= value <= 5):
            logging.warning(f"Program number {value} invalid: must be between 1 and 5")
            return
        self.client.write("RMP_SELECT", value)
    @RMP.scan(period=15, use_scan_field=True)
    async def RMP(self, instance: ChannelData, async_lib: AsyncLibraryLayer):
        async with self._communication_lock:
            await self.RMP_RBV.write(self.client.read("RMP_IN_05"))
    
    # Program start/stop
    RMP_Run = pvproperty(name="RMP_Run", doc="Start/stop selected program", dtype=bool, record='bi')
    RMP_Run_RBV = pvproperty(name="RMP_Run_RBV", doc="Readback program run state", dtype=bool, record='bi')
    @RMP_Run.putter
    async def RMP_Run(self, instance, value: bool):
        if isinstance(value, str):
            value = 1 if value.lower() in {'on', 'true'}
            value = 0 if value.lower() in {'off', 'false'}
        if bool(value):
            self.client.write("RMP_START", None)
        else:
            self.client.write("RMP_STOP", None)
    @RMP_Run.scan(period=15, use_scan_field=True)
    async def RMP_Run(self, instance: ChannelData, async_lib: AsyncLibraryLayer):
        async with self._communication_lock:
            pnum = self.client.read("RMP_IN_05")
            if int(float(pnum)) != 0:
                await self.RMP_Run_RBV.write(True)
            else:
                await self.RMP_Run_RBV.write(False)

def main(args=None):
    parser, split_args = template_arg_parser(
        default_prefix="Lauda:",
        desc="EPICS IOC for accessing the Lauda Proline RP855 over network",
    )

    if args is None:
        args = sys.argv[1:]

    parser.add_argument("--host", required=True, type=str, help="IP address of the host/device")
    parser.add_argument("--port", required=True, type=int, help="Port number of the device")

    args = parser.parse_args()

    logging.info("Running Lauda IOC")

    ioc_options, run_options = split_args(args)
    ioc = LaudaIOC(host=args.host, port=args.port, **ioc_options)
    run(ioc.pvdb, **run_options)


if __name__ == "__main__":
    main()
