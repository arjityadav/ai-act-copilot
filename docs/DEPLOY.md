# Deploying for free: Oracle Cloud Always Free + Groq

Target: one Ubuntu VM running `docker-compose.prod.yml` behind Caddy (automatic HTTPS).
- **Server:** Oracle Cloud **Always Free** Ampere (ARM) VM, Frankfurt region. $0 permanently.
- **LLM:** **Groq** free tier through the OpenAI-compatible API (no code changes: `OPENAI_BASE_URL`).
- **Embeddings:** `nomic-embed-text` on the VM's CPU (Ollama).

The same steps work on any Ubuntu server (only sections 1–2 are Oracle-specific).

## 0. Test Groq locally first
Structured output and rate limits are the risks with a free API, so check them on your machine
before deploying anything:
1. [console.groq.com](https://console.groq.com) → **API Keys** → create a key. Pick a model from the
   **Models** page (a Llama 3.x 70B "versatile" model is a good start) and look at the **Rate limits**
   page for its free-tier limits.
2. In your local `.env` (never committed):
   ```
   LLM_PROVIDERS=openai,ollama
   OPENAI_API_KEY=<groq key>
   OPENAI_BASE_URL=https://api.groq.com/openai/v1
   OPENAI_MODEL=<model id from the Models page>
   ```
3. Run a few scenarios. The app doesn't read `.env` by itself, so export it for the command:
   ```bash
   set -a; source .env; set +a
   uv run python evals/run_evals.py --only s01,s03,s07
   ```
   If you see HTTP 429 (rate limit), try a model with higher limits or fewer scenarios at a time.

## 1. Create the Oracle account
- [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) → Start for free.
- **Home region: Germany Central (Frankfurt).** This choice is **permanent**; Always Free
  resources only run in the home region.
- A card is required for identity verification. A free-tier account is not charged unless you
  upgrade it to Pay As You Go.
- Secure it: enable **MFA** for your user (Identity → your user → Multi-factor authentication).
- Billing & Cost Management → **Budgets**: create a budget with an alert at $1.

## 2. Create the VM
Compute → Instances → **Create instance**:
- **Image:** Canonical Ubuntu 24.04 (the ARM/aarch64 build is selected automatically for Ampere)
- **Shape:** Ampere → **VM.Standard.A1.Flex**, e.g. **2 OCPU / 12 GB** (Always Free allows up to
  4 OCPU / 24 GB in total; check the current limits on Oracle's Always Free page)
- **Networking:** create a new VCN with a **public subnet**, and **assign a public IPv4 address**
- **SSH keys:** "Generate a key pair for me" → **download the private key**, then
  `chmod 400 ssh-key.key` on your Mac
- Boot volume: the default (~47 GB) is within the free allowance

**"Out of host capacity"** is common for free ARM VMs. Try another availability domain, fewer
OCPUs (1 OCPU / 6 GB is enough for this app), or retry later.

### Open ports 80 and 443 (two firewalls)
Oracle has **two** layers, and both must allow the traffic:
1. **Cloud firewall:** Networking → Virtual Cloud Networks → your VCN → Security Lists →
   Default Security List → **Add Ingress Rules**: source `0.0.0.0/0`, TCP, destination port `80`;
   again for `443`. Edit the existing SSH rule (port 22) so the source is **your IP** (`x.x.x.x/32`).
2. **The VM's own firewall:** Oracle's Ubuntu images ship with iptables rules that only allow SSH.
   After you SSH in (section 3):
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
   Forgetting this layer is the most common reason an Oracle VM "doesn't respond" even though the
   security list is open.

Never open 5432 (Postgres) or 6379 (Redis).

## 3. Prepare the server
```bash
ssh -i ssh-key.key ubuntu@<public-ip>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && exit        # log out and SSH in again
```
(Add the two `iptables` lines from section 2 now.) With 6 GB+ RAM no swap is needed.

## 4. Configure
```bash
git clone https://github.com/arjityadav/ai-act-copilot.git && cd ai-act-copilot
cp deploy/env.prod.example .env.prod
nano .env.prod
```
- `DOMAIN`: the public IP **with dashes** + `.sslip.io` (e.g. `130-61-1-2.sslip.io`); it resolves to
  your IP, so Caddy can get a real HTTPS certificate without buying a domain
- `API_KEY`: `openssl rand -hex 32`; `POSTGRES_PASSWORD`: `openssl rand -hex 24`
- the Groq values from section 0

`.env.prod` is gitignored; it only ever lives on the server.

## 5. Start and ingest
```bash
alias dcp='docker compose -f docker-compose.prod.yml --env-file .env.prod'

dcp up -d --build                               # first build: several minutes on ARM
dcp exec ollama ollama pull nomic-embed-text
dcp ps                                          # all services running; db, redis, worker healthy

# Ingest the AI Act once. The image doesn't contain scripts/ or the corpus, so mount them
# (as root, because the script writes data/corpus/):
dcp run --rm --user root -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/data:/app/data" \
  api python scripts/ingest.py --file data/corpus/ai_act.txt
```
Expect `126 provisions · 292 chunks`. Migrations run automatically when the API starts.

## 6. Check
```bash
curl https://<DOMAIN>/health          # {"status":"ok"}
curl -X POST https://<DOMAIN>/chat -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" -d '{"question": "Is social scoring prohibited?"}'
```
Swagger UI: `https://<DOMAIN>/docs`.

## Operating it
| Task | Command |
|---|---|
| Logs | `dcp logs -f api worker` |
| Update to the latest `main` | `git pull && dcp up -d --build` |
| Stop (keeps data) | `dcp down` |
| Optional ML pre-screen | `scp -i ssh-key.key data/models/annex3.joblib ubuntu@<ip>:ai-act-copilot/data/models/`, then `dcp restart worker` |

Oracle may reclaim Always Free VMs that stay almost completely idle for a long time; a demo that
receives occasional traffic is normally fine (see Oracle's current Always Free policy).
