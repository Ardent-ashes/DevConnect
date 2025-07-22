# tcp_logger.py
import subprocess

def run_tcpdump_log():
    print("📡 Starting TCP dump to trace TCP packets on port 8080...\n")
    cmd = ["sudo", "tcpdump", "-i", "lo", "tcp port 8080", "-n", "-tt", "-l"]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in process.stdout:
            if "Flags" in line or "length" in line or "seq" in line:
                print(".", line.strip())
    except Exception as e:
        print(f"[tcpdump error] {e}")
