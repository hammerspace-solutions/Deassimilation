# 🧩 Deassimilation

Deassimilation is a Python utility to reverse the Hammerspace assimilation process by recreating directory structures and content from a DataSphere share onto a target storage volume, using NFS mounts and optional multiprocessing.

It connects to a Hammerspace Anvil node via its REST API to list volumes and shares, mounts the selected share and volume, and deassimilates files (hardlinks, symlinks, copies) back into a native filesystem layout.

## 🚀 Key Features

- REST API Integration: Queries Anvil for storage volumes and shares.
- Automated NFS Mounting: Mounts DataSphere share (NFSv4.2) and storage volume (NFSv3).
- Multiprocessing: Parallel file processing with configurable worker count.
- Operation Modes: Supports copy, link, and symlink deassimilation.
- Verification & Reporting: Optional size verification; directory/file statistics.
- Configurable Logging: Adjustable log levels for debugging or production use.

## 🛠️ Prerequisites

- Python 3.6+
- root privileges (for mounting/unmounting NFS).
- python-requests-toolbelt (e.g., apt-get install python-requests-toolbelt).
- Network access to the DataSphere Anvil node and storage exports.

## ⚙️ Installation

Do the following steps to install the software.

```
git clone https://github.com/hammerspace-solutions/Deassimilation.git
cd Deassimilation
./build-deassimilation.sh
source .venv/bin/activate
```

## 🧰 Usage

Run the script with the Anvil host specified. You must supply either --list-volumes to enumerate choices, or both --volid and --shareid to perform deassimilation:

### First Pass

```
deassimilate --host anvil.example.com --list-volumes
```

Write down the matching share and volume ID's

### Production Pass

```
deassimilate.py --host anvil.example.com --volid 10 --shareid 3 --mntdir /mnt/deassim --numjobs 50
```

The volid and shareid should match the volume and share returned from the first pass.

## 🔧 Command-Line Arguments

| Option | Description |
|----------------------------|-------------|
| --version | Show program version and exit. |
| --host <host> | Hostname or IP of the Hammerspace Anvil node (default: localhost). |
| --username <user> | Anvil username (default: admin). |
| --password <password> | Anvil password (will prompt if omitted). |
| --list-volumes | List available volumes and shares, then exit. |
| --volid <id> | Storage Volume ID to deassimilate to (internal ID). |
| --shareid <id> | Share ID to deassimilate to (internal ID). |
| --mntdir <path> | Base directory for NFS mountpoints (default: /mnt/deassim). |
| --numjobs <n> | Number of parallel worker processes (default: 50). |
| --single-process | Run in a single process (disable multiprocessing). |
| --statistics | Print per-directory and per-file statistics. |
| --totals | Print total counts of directories, files, and size. |
| --log <level> | Set logging level (DEBUG, INFO, WARNING, ERROR; default: INFO). |

## ⚠️ Warnings

- This script requires root and NFS write access to both the Anvil and storage volumes.
- Avoid running directly on the Anvil or DSX nodes—use a separate NFS-capable client or VM.
- High parallelism (--numjobs) may impact storage performance; test for optimal value.

## 📌 Known Limitations

- Cannot preserve ctime or symlink-specific metadata due to API/NFS restrictions.
- No built-in checksum validation (beyond size) or resume capability.
- Device files, pipes, sockets, and Windows ACLs are not supported.

## 🧭 Roadmap

- Add checksum-based verification and resume support.
- Implement fix-up script generation for error recovery.
- Enhance metadata fidelity (xattrs, POSIX permissions).
- Web UI or dry-run report mode.

## 🤝 Contributing

Contributions welcome! Fork the repo, create feature branches, and open pull requests. Please open issues to discuss major changes.

## 📜 License

This project is licensed under the MIT License. See LICENSE for details.