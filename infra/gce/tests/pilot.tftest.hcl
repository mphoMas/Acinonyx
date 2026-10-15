# Local mocked planning checks only: no cloud authentication, resources or costs.
mock_provider "google" {}

run "private_single_host_pilot" {
  command = plan
  variables {
    project_id = "mas-local-qualification"
  }

  assert {
    condition     = google_compute_instance.pilot.machine_type == "e2-standard-4"
    error_message = "The reviewed initial pilot envelope is 4 vCPU / 16 GiB."
  }
  assert {
    condition     = google_compute_instance.pilot.deletion_protection
    error_message = "The pilot VM must retain deletion protection."
  }
  assert {
    condition     = google_compute_disk.state.size == 100 && google_compute_disk.state.type == "pd-balanced"
    error_message = "The pilot needs its separate reviewed 100 GiB persistent state disk."
  }
  assert {
    condition     = google_compute_firewall.iap_ssh.source_ranges == toset(["35.235.240.0/20"])
    error_message = "Only IAP tunnel ingress may reach SSH."
  }
  assert {
    condition     = length(google_compute_firewall.iap_ssh.allow) == 1 && alltrue([for rule in google_compute_firewall.iap_ssh.allow : rule.protocol == "tcp" && length(rule.ports) == 1 && contains(rule.ports, "22")])
    error_message = "The infrastructure must not open an application or Docker port."
  }
  assert {
    condition     = length(one(google_compute_instance.pilot.service_account).scopes) == 0
    error_message = "The VM must not receive API scopes before identity admission."
  }
  assert {
    condition     = google_compute_instance.pilot.metadata["enable-oslogin"] == "TRUE" && google_compute_instance.pilot.metadata["block-project-ssh-keys"] == "TRUE"
    error_message = "Operator access must retain OS Login and reject project SSH keys."
  }
}
