terraform {
  required_version = ">= 1.13.3, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

variable "project_id" {
  type        = string
  description = "Actual Google Cloud project ID; Firebase access alone does not establish Compute Engine or billing permissions."
}

variable "region" {
  type    = string
  default = "africa-south1"
}

variable "zone" {
  type    = string
  default = "africa-south1-a"
}

variable "name" {
  type    = string
  default = "mas-core-pilot"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,19}$", var.name))
    error_message = "Use 5–20 lowercase letters, digits or hyphens, starting with a letter."
  }
}

resource "google_project_service" "required" {
  for_each           = toset(["compute.googleapis.com", "iam.googleapis.com", "iap.googleapis.com", "oslogin.googleapis.com"])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "pilot" {
  name                    = var.name
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required]
}

resource "google_compute_subnetwork" "pilot" {
  name          = var.name
  region        = var.region
  network       = google_compute_network.pilot.id
  ip_cidr_range = "10.42.0.0/24"
}

resource "google_compute_firewall" "iap_ssh" {
  name          = "${var.name}-iap-ssh"
  network       = google_compute_network.pilot.name
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = [var.name]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# This fresh VM identity receives no project IAM role or secret access here.
resource "google_service_account" "runtime" {
  account_id   = "${var.name}-vm"
  display_name = "MAS pilot VM; no application credentials or project roles"
  depends_on   = [google_project_service.required]
}

data "google_compute_image" "debian" {
  project    = "debian-cloud"
  family     = "debian-12"
  depends_on = [google_project_service.required]
}

resource "google_compute_disk" "state" {
  name       = "${var.name}-state"
  zone       = var.zone
  type       = "pd-balanced"
  size       = 100
  depends_on = [google_project_service.required]
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_instance" "pilot" {
  name                = var.name
  machine_type        = "e2-standard-4"
  zone                = var.zone
  deletion_protection = true
  tags                = [var.name]

  boot_disk {
    initialize_params {
      image = data.google_compute_image.debian.self_link
      type  = "pd-balanced"
      size  = 30
    }
  }
  attached_disk {
    source      = google_compute_disk.state.id
    device_name = "mas-core-data"
  }
  network_interface {
    subnetwork = google_compute_subnetwork.pilot.id
    # External IPv4 supplies outbound package/provider access. No application
    # ingress firewall exists; operator access uses authenticated IAP SSH.
    access_config {}
  }
  service_account {
    email  = google_service_account.runtime.email
    scopes = []
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  }
  metadata_startup_script = file("${path.module}/bootstrap.sh")
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  allow_stopping_for_update = true
}

output "pilot" {
  value = {
    project        = var.project_id
    instance       = google_compute_instance.pilot.name
    zone           = var.zone
    machine_type   = google_compute_instance.pilot.machine_type
    data_disk      = google_compute_disk.state.name
    selected_image = data.google_compute_image.debian.self_link
  }
}
