variable "image" {
  type        = string
  description = "vick Docker image to run"
  default     = "ghcr.io/bencevans/vick:latest"
}

variable "config" {
  type        = string
  description = "Full contents of vick's config.toml (see config.example.toml)"
}

variable "metrics_port" {
  type        = number
  description = "Host port to expose the Prometheus /metrics endpoint on"
  default     = 9101
}

job "vick" {
  datacenters = ["ldy0"]
  type        = "service"

  group "vick" {
    count = 1

    # BLE access relies on the host's BlueZ stack over D-Bus.
    constraint {
      attribute = "${attr.kernel.name}"
      value     = "linux"
    }

    network {
      port "metrics" {
        static = var.metrics_port
        to     = 9101
      }
    }

    task "vick" {
      driver = "docker"

      config {
        image = var.image
        args  = ["--config", "/local/config.toml", "-v"]
        ports = ["metrics"]

        # Bind-mounting the host's D-Bus socket is how the container talks to
        # bluetoothd; no --privileged or host networking is required.
        mount {
          type     = "bind"
          source   = "/var/run/dbus"
          target   = "/var/run/dbus"
          readonly = false
        }
      }

      template {
        data        = var.config
        destination = "local/config.toml"
      }

      service {
        provider = "nomad"
        name     = "vick-metrics"
        port     = "metrics"

        check {
          type     = "http"
          path     = "/metrics"
          interval = "30s"
          timeout  = "5s"
        }
      }

      resources {
        cpu    = 100
        memory = 128
      }
    }
  }
}
