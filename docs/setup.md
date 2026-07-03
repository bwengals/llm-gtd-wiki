# Setup

End-to-end: deploy the infra, seed a wiki, connect the Claude apps, and (optionally) set up laptop
editing. Assumes an AWS account and an Anthropic **Max** plan.

## Prerequisites
- AWS credentials configured locally (`aws sts get-caller-identity` works). The identity needs to
  create Cognito, Lambda, API Gateway, IAM, S3, and CloudWatch resources.
- Terraform ≥ 1.7, Python 3.12, `zip`.
- The Claude desktop + phone apps, plus **claude.ai on the web** (connectors are *added* on the web).

## 1. Build the Lambda package
```bash
cd server
python -m pip install --upgrade pip
bash scripts/package.sh          # -> server/dist/lambda.zip
```

## 2. Deploy
```bash
cd ../infra
cp terraform.tfvars.example terraform.tfvars   # edit: cognito_domain_prefix, bucket_name (both
                                               #       globally unique), owner_email, region
terraform init
terraform apply
```
Note the outputs: `connector_url`, `cognito_user_pool_id`, `cognito_hosted_ui`.

## 3. Seed a starter wiki
```bash
cd ..
scripts/seed_wiki.sh <bucket_name>     # uploads template/wiki/ (refuses a non-empty bucket)
```

## 4. Set your login password
Cognito emails a temporary password to `owner_email`, or set one directly:
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id <cognito_user_pool_id> --username <owner_email> \
  --password '<a-strong-password>' --permanent --region <region>
```

## 5. Add the connector (on claude.ai WEB)
Settings → Connectors → **Add custom connector** → paste `connector_url` → complete the Cognito
login. Connectors are added on the web and **sync to desktop + mobile automatically** (you can't add
one in the phone app, only use it). See [connector-oauth.md](connector-oauth.md) if the handshake
fails.

## 6. Create the Claude Project
Make a "LifeTracker" Project and paste [`template/project-instructions.md`](../template/project-instructions.md)
as its custom instructions. See [claude-project.md](claude-project.md).

## 7. Personalize (bootstrap)
In the Project, paste [`template/BOOTSTRAP.md`](../template/BOOTSTRAP.md) — it interviews you, fills
the `CLAUDE.md` placeholders, and does a first pass.

## 8. Email & calendar
Not built here — enable Anthropic's first-party **Gmail** and **Google Calendar** connectors in the
app alongside this one. Claude uses all three together.

## 9. (Optional) Laptop editing
For structural/bulk changes or running scripts, use a local clone with Claude Code, bracketed by
sync. See [laptop-sync.md](laptop-sync.md). Copy `scripts/wiki-sync.env.example` → `wiki-sync.env`,
then `wiki-pull.sh` at the start and `wiki-push.sh` at the end.

## Verify
- `curl <base>/.well-known/oauth-authorization-server` → JSON (200).
- In the app: "call `list_files`" → your files; "add to inbox: test" → then read `inbox.md`.
