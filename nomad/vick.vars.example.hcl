image        = "ghcr.io/bencevans/vick:latest"
metrics_port = 9101

# Full contents of vick's config.toml — see ../config.example.toml.
# Copy this file to vick.vars.hcl (gitignored) and fill in real values, then:
#   nomad job run -var-file=nomad/vick.vars.hcl nomad/vick.nomad.hcl
config = <<EOF
[[devices]]
name = "starter-battery"
address = "AA:BB:CC:DD:EE:FF"
key = "abcdef0123456789abcdef0123456789"

[reporting.prometheus]
enabled = true
port = 9101
EOF
