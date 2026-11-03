# DNS ISP Failover

A Linux/Python monitor that probes two ISP paths and updates an authoritative DNS A record using an RFC 2136 dynamic update signed with TSIG HMAC-SHA256. The original monitoring code is preserved in `monitor.py`.

## Requirements

- Python 3.10+ and `dnspython` (see `requirements.txt`).
- Linux `ping` (typically the `iputils-ping` package) and the required ICMP permissions.
- Both configured source IP addresses assigned locally, with routing/policy routing that sends each probe through its intended ISP. Binding a source IP alone does not guarantee ISP selection.
- A DNS server reachable on TCP port 53 that accepts dynamic updates to the zone/record using the `failover-key.` TSIG key with HMAC-SHA256. Restrict the update policy to the required record/type.

## Configure

Edit `DNS_SERVER`, `ZONE`, `RECORD`, `TTL` and the `ISPS` probe targets/source IPs in `monitor.py` for your environment. The defaults are illustrative.

Set the required environment variables:

- `SHATEL_PUBLIC_IP`: public IPv4 address for the primary ISP.
- `ASIA_PUBLIC_IP`: public IPv4 address for the backup ISP.
- `TSIG_SECRET`: base64-encoded TSIG shared secret.

An `.env.example` is provided with documentation-only IP addresses. The Python script does **not** automatically load `.env` files.

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
chmod 600 .env
# Edit .env locally with trusted values before continuing.
# The following sources .env as shell code; only source files you trust.
set -a
. ./.env
set +a

python monitor.py
```

Do not run this against a production DNS zone until routing, health checks and dynamic-update authorization have been tested in a lab. No live network or DNS-update test is included in this repository.

## Behavior and limitations

- Primary ISP: `shatel`; failure threshold: 3 consecutive failed probe rounds.
- Each probe sends two ICMP echo requests. A successful `ping` process counts as a healthy round; this does not mean every packet succeeded.
- Probes run sequentially. Each round sleeps 10 seconds **after** probing and any DNS update, so detection time is not exactly 30 seconds.
- At startup, a path below the failure threshold is eligible even before three failures establish an outage. The script does not require a successful health check before its first update.
- Primary failback occurs after a single successful primary probe round; there is no separate recovery threshold or hold-down timer.
- The first eligible path triggers a DNS update because in-memory `active` starts as `None` on every restart.
- If all paths exceed the failure threshold, the script logs a warning and leaves the existing DNS record unchanged.
- A nonzero DNS response code returns `False` without a dedicated error log; exceptions during updates are logged and retried on later rounds.
- This is DNS steering, not routing/NAT failover. Existing sessions are not migrated. Recursive and client caching mean a TTL of 30 is not a guaranteed failover deadline.
- Each public IP must independently reach the application through appropriate routing, NAT and firewall configuration. ICMP reachability alone does not prove application availability.
- The DNS service must be part of the authoritative resolution path for the application; changing an unrelated local zone will not change public DNS resolution.

## Security

Keep `.env` and the TSIG secret out of Git. Use an account and filesystem permissions appropriate to the deployment, and give the TSIG key the narrowest possible DNS update permissions. The script does not require a GitHub token at runtime.
