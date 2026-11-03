import logging, os, subprocess, time
import dns.update, dns.query, dns.tsig, dns.tsigkeyring

FAIL_THRESHOLD, CHECK_INTERVAL = 3, 10
PRIMARY = "shatel"

DNS_SERVER = "192.168.1.10"
ZONE = "example.com"
RECORD = "app.example.com."
TTL = 30

ISPS = {
    "shatel": {"target": "1.1.1.1", "src_ip": "10.10.0.2", "public_ip": os.environ["SHATEL_PUBLIC_IP"]},
    "asia":   {"target": "8.8.8.8", "src_ip": "10.20.0.2", "public_ip": os.environ["ASIA_PUBLIC_IP"]},
}

def check_isp(cfg):
    r = subprocess.run(
        ["ping", "-c", "2", "-W", "2", "-I", cfg["src_ip"], cfg["target"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0

def update_dns(new_ip):
    keyring = dns.tsigkeyring.from_text({"failover-key.": os.environ["TSIG_SECRET"]})
    update = dns.update.Update(ZONE, keyring=keyring, keyname="failover-key.",
                               keyalgorithm=dns.tsig.HMAC_SHA256)
    update.replace(RECORD, TTL, "A", new_ip)
    return dns.query.tcp(update, DNS_SERVER, timeout=5).rcode() == 0

def monitor():
    active, fails = None, {name: 0 for name in ISPS}
    while True:
        for name, cfg in ISPS.items():
            fails[name] = 0 if check_isp(cfg) else fails[name] + 1

        desired = PRIMARY if fails[PRIMARY] < FAIL_THRESHOLD else next(
            (n for n in ISPS if n != PRIMARY and fails[n] < FAIL_THRESHOLD), None)

        if desired and desired != active:
            try:
                if update_dns(ISPS[desired]["public_ip"]):
                    logging.info("Switched DNS to %s", desired)
                    active = desired
            except Exception:
                logging.exception("DNS update failed for %s", desired)
        elif desired is None:
            logging.warning("All ISPs down!")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    monitor()
