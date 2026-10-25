# First cloud session: resource and cost draft

No cloud resources have been created. Proposed first session: one ordinary N2D
VM and one SEV-SNP N2D VM in `us-central1-a`, each 8 vCPUs, 64 GiB memory and a
300 GiB SSD persistent boot disk, for at most six hours each. No bucket, snapshot,
reserved IP or extra disk is included. This is 12 machine-hours, not six.

Public USD on-demand list prices checked 2026-10-25:

| Component | Calculation | USD / pair-hour |
|---|---|---:|
| Two n2d-highmem-8 VMs | 2 × 0.45592 | 0.9118400 |
| SNP surcharge on one VM | 8 × 0.0027502 + 64 × 0.0003686 | 0.0455920 |
| Two 300 GiB pd-ssd disks | 600 × 0.000232877 | 0.1397262 |
| Two in-use ephemeral IPv4 addresses | 2 × 0.005 | 0.0100000 |
| Total, excluding transfer/tax/other services | | **1.1071582** |

The six-hour pair totals approximately **$6.64**. A proposed first-session
operating budget is **$15**, leaving room for transfer and unexpected overhead.
This is an estimate and operational limit, not a provider-enforced billing cap.
Recheck project-specific rates and prices before launch. Export only small
summaries, not large alignment files, unless transfer cost has been budgeted.
An additional session is a separate decision after the first results.

Sources: [Iowa N2D table](https://cloud.google.com/products/compute/pricing/general-purpose?hl=en),
[SNP surcharge](https://cloud.google.com/confidential-computing/confidential-vm/pricing),
[SSD storage](https://cloud.google.com/compute/disks-image-pricing),
[in-use IPv4](https://cloud.google.com/vpc/network-pricing).

Authentication, project choice, exact SNP-capable image, ordinary-VM NVMe boot
support, and deletion-deadline compatibility remain to be confirmed. The draft
sets a six-hour deletion deadline as a backstop, then explicitly deletes the
pair and checks for leftover disks. Stop a session early when usable results
are obtained. A stopped VM's retained disk still costs money.
