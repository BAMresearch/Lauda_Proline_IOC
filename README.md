# Lauda_Proline_IOC
A Caproto IOC for basic control of the Lauda Proline RP855C bath.

This project implements an EPICS IOC for interfacing with the Lauda Proline RP855 device over a network using their simple ASCII protocol. The IOC is built using [Caproto](https://github.com/caproto/caproto) and Python's asynchronous features to communicate with the device over a TCP/IP socket.

## Features

- **EPICS Process Variables (PVs):**  
  Defines multiple PVs for setting and reading device parameters (e.g., temperature setpoint, bath temperature, operating mode, and program selection).

- **Periodic Scanning:**  
  Several PVs are updated periodically (every 15 seconds) using Caproto's scan decorators to ensure the IOC reflects the current device status.

- **Input Validation and Logging:**  
  Validates IP address and port inputs; includes logging at INFO and DEBUG levels for monitoring device communication.

## Available IOC PVs

| PV Name         | Description                                                  | Scannable?                     |
|-----------------|--------------------------------------------------------------|--------------------------------|
| **TSET**        | Temperature setpoint (write-only)                            | Yes (output in TSET_RBV)          |
| **TSET_RBV**    | Setpoint readback (updates via scan, based on command \`IN_SP_00\`) | No                            |
| **T_RBV**       | Bath temperature readback (updates via scan, based on command \`IN_PV_00\`) | Yes                            |
| **Run**         | Chiller operating mode control (write-only)                  | Yes (output in Run_RBV)          |
| **Run_RBV**     | Operating mode readback (updates via scan, based on command \`IN_MODE_02\`) | No                            |
| **RMP**         | Run program selection (values 1-5, write-only)               | Yes (output in RMP_RBV)          |
| **RMP_RBV**     | Readback of selected run program (updates via scan, based on command \`RMP_IN_05\`) | No                            |
| **RMP_Run**     | Start/Stop selected program control (write-only)             | Yes (output in RMP_Run_RBV)          |
| **RMP_Run_RBV** | Program run state readback (updates via scan, based on command \`RMP_IN_05\`) | No                            |

*Note:* The scan methods for readback PVs update every 15 seconds by default. Adjust the period if needed.

## Dependencies

- **Python 3.11+**  
- **Caproto:** EPICS communication framework ([GitHub Repository](https://github.com/caproto/caproto))
- **attrs:** For cleaner class definitions ([Documentation](https://www.attrs.org/en/stable/))
- Standard libraries: \`asyncio\`, \`socket\`, \`logging\`, \`sys\`, \`datetime\`

## Installation

1. **Clone the Repository:**

   \`\`\`bash
   git clone https://github.com/yourusername/lauda-ioc.git
   cd lauda-ioc
   \`\`\`

2. **(Optional) Create and Activate a Virtual Environment:**

   \`\`\`bash
   python3 -m venv .venv &&
   source .venv/bin/activate
   \`\`\`

3. **Install Required Packages:**

   \`\`\`bash
   pip install caproto attrs
   \`\`\`

## Configuration

The IOC accepts the target device's IP address and port as command-line arguments. Default values are provided in the code but can be overridden.

## Usage

To start the IOC, run:

\`\`\`bash
python LaudaProlineIOC.py --prefix Lauda: --list-pvs --host <DEVICE_IP> --port <PORT_NUMBER>
\`\`\`

For example:

\`\`\`bash
python lauda_ioc.py --prefix Lauda: --list-pvs --host 172.17.1.14 --port 4014
\`\`\`

The IOC will connect to the Lauda Proline RP855 device and begin periodic scanning to update readback PVs.

## Logging

Logging is configured to display INFO-level messages by default. Modify the logging configuration in the source code if you require additional debug output.

## Making This README Available for Download

Once this README.md is included in your repository (e.g., on GitHub), users can easily download the entire repository or the individual file via the platform’s file interface.

## Contributing

Contributions, bug reports, and feature requests are welcome. Please open an issue or submit a pull request to improve this project.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
`
