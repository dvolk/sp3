# Walkthrough describing how to install SP3 on Oracle Cloud infrastructure

This assumes you already have an OCI account; the below was done using a Free Trial account. You'll also need to have created an `SSH` keypair on your local machine.

## Create a Virtual Cloud Network

For brevity I won't include screenshots but will provide 'piped' instructions where the three horizonal lines in the top left of the OCI console will be called "Hamburger".

To begin: `Hamburger | Networking | Virtual Cloud Network | Create VCN`. Give it a name you'll remember and then click `Create VCN`.

## Spin up an OCI instance for the SP3 server

Now: `Hamburger | Compute | Instances | Create Instance`

You'll need to tweak the default options:
* change the image to Ubuntu 18.04 LTS
* select an appropriate compute Shape e.g. `VM.Standard2.1`. If you are using a Free Trial, you are limited to 6 OCPUs per availability domain so don't make your server too large.
* make sure the Virtual cloud network you created above has been selected (it probably has automatically)
* check that `Assign a public IPv4 address` is marked `Yes`.
* paste or copy your public `SSH` key into the box

Click `Create`. It can take a few minutes to spin up. Partway through the process the `Public IP` address will be shown. Then you can try connecting

`$ ssh ubuntu@132.145.40.84`

## Create an `SSH` key pair on your new VM

`$ ssh-keygen -t rsa`

and add the public key to your GitLab profile.

## Clone and install SP3

```
$ git clone git@gitlab.com:MMMCloudPipeline/sp3.git
$ cd sp3/sp3doc/
$ bash install.bash
```

## Create and add some block storage

In the OCI console, go to: `Hamburger | Block Storage | Block Volumes` and click `Create Block Volume`. We created two called `data` and `work`, each 100GB.

Now if you click each in turn and click `Attached Instances | Attach to Instance` and choose the VM you spun up above. We chose `paravirtualised` and `/dev/oracleoci/oraclevdb`. Repeat for the other but with `/dev/oracleoci/oraclevdc`.

## Now format the discs and attach them to the VM

Use the default options for the first. Note that a '1' is appended!

```
$ sudo fdisk /dev/oracleoci/oraclevdb
$ sudo mkfs.ext3 /dev/oracleoci/oraclevdb1
$ sudo mount /dev/oracleoci/oraclevdb1 /data
```

..and repeat for `vdc` -> `/work`. Now if you run `df` you should see them.

```
$ df -h
...
/dev/sdb1       984G   73M  934G   1% /data
/dev/sdc1       984G   73M  934G   1% /work
```

## Install the `oci` CLI on the VM

```
$ bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
```

## Now setup the `oci` CLI

For this you need to know your user OCID and tenancy OCID which you can find out via clicking your Profile (top right) and then the first option (which has your email) to get your user OCID and the second option. The `XXXXXX`s you need to replace below and you also need to specify the right region.

```
$ oci setup config
...
Enter a location for your config [/home/ubuntu/.oci/config]:
Enter a user OCID: ocid1.user.oc1..XXXXXXX
Enter a tenancy OCID: ocid1.tenancy.oc1..XXXXX
Enter a region by index or name(e.g.
1: ap-chiyoda-1, 2: ap-chuncheon-1, 3: ap-hyderabad-1, 4: ap-melbourne-1, 5: ap-mumbai-1,
6: ap-osaka-1, 7: ap-seoul-1, 8: ap-sydney-1, 9: ap-tokyo-1, 10: ca-montreal-1,
11: ca-toronto-1, 12: eu-amsterdam-1, 13: eu-frankfurt-1, 14: eu-zurich-1, 15: me-dubai-1,
16: me-jeddah-1, 17: sa-santiago-1, 18: sa-saopaulo-1, 19: uk-cardiff-1, 20: uk-gov-cardiff-1,
21: uk-gov-london-1, 22: uk-london-1, 23: us-ashburn-1, 24: us-gov-ashburn-1, 25: us-gov-chicago-1,
26: us-gov-phoenix-1, 27: us-langley-1, 28: us-luke-1, 29: us-phoenix-1, 30: us-sanjose-1): uk-london-1
Do you want to generate a new API Signing RSA key pair? (If you decline you will be asked to supply the path to an existing key.) [Y/n]:
Enter a directory for your keys to be created [/home/ubuntu/.oci]:
Enter a name for your key [oci_api_key]:
Public key written to: /home/ubuntu/.oci/oci_api_key_public.pem
Enter a passphrase for your private key (empty for no passphrase):
Private key written to: /home/ubuntu/.oci/oci_api_key.pem
Fingerprint: 42:30:ee:c2:ae:42:ea:f7:f6:e1:f1:09:55:9f:f2:14
Config written to /home/ubuntu/.oci/config
```

Check via

```
$ oci os ns get
```

## Setup the NFS share on the headnode

```
sudo apt-get install nfs-server
```

add the following /etc/exports
```
/work 10.0.0.0/255.255.255.0(rw,async,root_squash)
/data 10.0.0.0/255.255.255.0(ro,async,root_squash)
```

```
sudo systemctl restart nfs-server.service
sudo systemctl status nfs-server.service
```

**Important**: not setup the NFS firewall correctly.


## Setup `catcloud`

First check that the service files have been copied into place and if not copy them manually

```
$ ls /home/ubuntu/.config
$ mkdir /home/ubuntu/.config
$ mkdir /home/ubuntu/.config/systemd
$ mkdir /home/ubuntu/.config/systemd/user
$ cp /home/ubuntu/sp3/sp3doc/systemd/*.service /home/ubuntu/.config/systemd/user/
$ systemctl --user daemon-reload
$ systemctl --user restart catgrid
```

Now we are in a position to setup `catcloud`

```
$ cd sp3/catcloud
$ cp config.yaml-example config.yaml
$ emacs config.yaml
$ cd scripts/
$ emacs scripts/oracle_node_setup.sh
```

and start it

```
python3 main.py --profile oracle-test
```
