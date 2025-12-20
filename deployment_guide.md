# GCP Free Tier Deployment Guide

This guide will walk you through deploying your `Robin Trading Bot` and `Dashboard` to a **Google Cloud Platform (GCP) "Running Always Free"** VM instance.

## 1. Create GCP Project and VM

1.  **Go to Google Cloud Console:** [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  **Create a New Project:** Click the project selector in the top left -> "New Project" -> Name it (e.g., `trading-bot`) -> Create.
3.  **Enable Compute Engine:**
    *   Navigate to **Menu** > **Compute Engine** > **VM Instances**.
    *   Click **Enable** (this may take a minute).
4.  **Create VM Instance:**
    *   Click **Create Instance**.
    *   **Name:** `robin-bot`
    *   **Region:** Must be one of `us-west1`, `us-central1`, or `us-east1` (Required for Free Tier).
    *   **Zone:** Any zone in that region (e.g., `us-west1-b`).
    *   **Machine Type:** `e2-micro` (2 vCPU, 1 GB memory) - *Look for the "Low cost" label*.
    *   **Boot Disk:**
        *   Click "Change".
        *   Operating System: **Ubuntu**.
        *   Version: **Ubuntu 22.04 LTS (x86/64)**.
        *   Disk Type: **Standard persistent disk**.
        *   Size: **30 GB** (Free tier allows up to 30GB).
        *   Click **Select**.
    *   **Firewall:** Check "Allow HTTP traffic" and "Allow HTTPS traffic".
    *   Click **Create**.

## 2. Configure Firewall (Open Port 5000)

To see your dashboard, you need to open port 5000.
> [!WARNING]
> Opening port 5000 allows the public internet to access your dashboard. Since your dashboard currently has no password protection, anyone with the IP can see it.

1.  Go to **VPC network** > **Firewall**.
2.  Click **Create Firewall Rule**.
3.  **Name:** `allow-dashboard`
4.  **Targets:** "All instances in the network".
5.  **Source IPv4 ranges:** `0.0.0.0/0` (Allows access from anywhere).
6.  **Protocols and ports:** Check "TCP" and enter `5000`.
7.  Click **Create**.

## 3. Connect to VM and Setup Environment

1.  Go back to **VM Instances**.
2.  Click the **SSH** button next to your `robin-bot` instance. A terminal window will open.
3.  **Create a folder for your bot:**
    ```bash
    mkdir robin_bot
    cd robin_bot
    ```

## 4. Upload Files

You need to move your files from your local computer to the VM.
**Option A: Using the SSH Browser (Easiest)**
1.  In the SSH window, click the **Gear Icon** (top right) > **Upload file**.
2.  Use the artifacts created in this chat to upload these specific files first:
    *   `setup_vm.sh`
    *   `bot.service`
    *   `dashboard.service`
3.  Then upload all your Python files (`bot.py`, `server.py`, `config.py`, etc.).
    *   *Note: You may need to zip your local folder, upload the zip, and unzip it if you have many files.*
    *   To unzip on VM: `sudo apt-get install unzip` then `unzip filename.zip`.

## 5. Run Setup Script

Once `setup_vm.sh` is uploaded to the VM:

1.  **Make it executable:**
    ```bash
    chmod +x setup_vm.sh
    ```
2.  **Run it:**
    ```bash
    ./setup_vm.sh
    ```
    *This will update the system and install all required Python libraries.*

## 6. Configure Systemd Services

We will use `systemd` to keep your bot running 24/7, even if it crashes or the VM restarts.

1.  **Edit the service files:**
    *   The service files (`bot.service`, `dashboard.service`) assume your username is part of the path.
    *   Run `whoami` in the terminal to get your username.
    *   The service files I created use `%u` which automatically fills this in, so **they should work without editing** as long as your files are in `~/robin_bot`.

2.  **Move service files to system folder:**
    ```bash
    sudo mv bot.service /etc/systemd/system/
    sudo mv dashboard.service /etc/systemd/system/
    ```

3.  **Reload and Start:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable bot
    sudo systemctl enable dashboard
    sudo systemctl start bot
    sudo systemctl start dashboard
    ```

4.  **Check Status:**
    ```bash
    sudo systemctl status bot
    sudo systemctl status dashboard
    ```
    *You should see "Active: active (running)" in green.*

## 7. Access Your Dashboard

1.  Go back to the GCP Console **VM Instances** page.
2.  Find the **External IP** of your instance.
3.  Open your browser and go to: `http://<YOUR_EXTERNAL_IP>:5000`

**Congratulations! Your bot is now running 24/7 on the cloud.**

---

## Troubleshooting commands
- **View Bot Logs:** `journalctl -u bot -f`
- **View Dashboard Logs:** `journalctl -u dashboard -f`
- **Restart Bot:** `sudo systemctl restart bot`
