import os
import subprocess


class SystemController:

    @staticmethod
    def service_action(action, name):
        if action not in {"start", "stop", "restart", "status"}:
            return False, f"Invalid action: {action}"
        try:
            r = subprocess.run(["systemctl", action, name],
                               capture_output=True, text=True, timeout=30)
            return (True, f"{name}: {action} done") if r.returncode == 0 \
                   else (False, r.stderr.strip() or f"Error: {action} {name}")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_disable():
        """Stop SSH service AND socket so it doesn't restart via socket activation."""
        try:
            for unit in ["ssh.socket", "ssh"]:
                subprocess.run(["systemctl", "stop",    unit], timeout=10)
                subprocess.run(["systemctl", "disable", unit], timeout=10)
            return True, "SSH stopped (service + socket)"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def ssh_enable():
        try:
            for unit in ["ssh.socket", "ssh"]:
                subprocess.run(["systemctl", "enable", unit], timeout=10)
            subprocess.run(["systemctl", "start", "ssh.socket"], timeout=10)
            return True, "SSH started (service + socket)"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_autostart_services():
        try:
            r = subprocess.run(
                ["systemctl", "list-unit-files", "--type=service",
                 "--state=enabled", "--no-pager", "--no-legend"],
                capture_output=True, text=True, timeout=15)
            return [l.split()[0].replace(".service", "")
                    for l in r.stdout.strip().splitlines() if l.split()]
        except Exception:
            return []

    @staticmethod
    def reboot_server():
        try:
            subprocess.Popen(["bash", "-c", "sleep 5 && shutdown -r now"])
            return True, "ok"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def clear_journal():
        try:
            r = subprocess.run(["journalctl", "--vacuum-time=1d"],
                               capture_output=True, text=True, timeout=60)
            return True, r.stdout.strip() or "Logs cleared"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def close_port(port):
        try:
            r = subprocess.run(["lsof", "-ti", f":{port}"],
                               capture_output=True, text=True, timeout=10)
            pids = [p for p in r.stdout.strip().splitlines() if p]
            if not pids:
                return False, f"Port {port} not in use"
            for pid in pids:
                subprocess.run(["kill", "-9", pid], timeout=5)
            return True, f"Port {port} closed ({len(pids)} processes killed)"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def add_ssh_key(pubkey, username="root"):
        try:
            import pwd
            try:
                pw = pwd.getpwnam(username)
                home, uid, gid = pw.pw_dir, pw.pw_uid, pw.pw_gid
            except KeyError:
                home, uid, gid = "/root", 0, 0
            ssh_dir   = home + "/.ssh"
            auth_file = ssh_dir + "/authorized_keys"
            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
            os.chown(ssh_dir, uid, gid)
            existing = open(auth_file).read() if os.path.exists(auth_file) else ""
            if pubkey.strip() in existing:
                return False, "Key already exists"
            with open(auth_file, "a") as f:
                f.write("\n" + pubkey.strip() + "\n")
            os.chmod(auth_file, 0o600)
            os.chown(auth_file, uid, gid)
            return True, f"SSH key added for {username}"
        except Exception as e:
            return False, str(e)
