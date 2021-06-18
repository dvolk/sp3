#!/usr/bin/env python3
import oci
from argparse import ArgumentParser, SUPPRESS

def getFiles(bucket, user, keyfile):
    # use oci to list all the files in bucket with prefix 'meta'
    region='uk-london-1'
    fingerprint='54:dc:f9:d2:22:79:43:17:2c:2c:7a:15:fe:bc:a1:f8'
    keyfile='/home/ubuntu/.oci/oci_api_key.pem'
    tenancy='ocid1.tenancy.oc1..aaaaaaaa4mcyyn2h7c37qyuq5ttoaeb4mh4cuprqnlsmmcirop5hgl3ehrvq'
    config = {
        "user": user,
        "key_file": keyfile,
        "fingerprint": fingerprint,
        "tenancy": tenancy,
        "region": region 
        }
    
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    
    namespace = object_storage_client.get_namespace().data
    
    object_list = object_storage_client.list_objects(namespace,bucket,
            prefix='meta')
    
    # to try and get more than 1000 files, doesn't work yet
    while object_list.has_next_page:
        object_list.extend( object_storage_client.list_objects(namespace,bucket, 
                    prefix='meta',
                    start=object_list.nextStartWith) )
    
    # create dictionary of files using meta data from head_object
    d={}
    for o in object_list.data.objects:
        head_object_response = object_storage_client.head_object(namespace_name=namespace,
                bucket_name=bucket,
                object_name=o.name)
        run=head_object_response.headers['opc-meta-run']
        sampleID=head_object_response.headers['opc-meta-sampleID']
        d[o.name]={'name':o.name,
                'run':run,
                'sampleID':sampleID}
    return d

def groupFiles(d):
    # iterate through dictionary to group files by runs and samples
    runs={}

    for f in d:
        runs.setdefault(d[f]['run'],{}).setdefault(d[f]['sampleID'],[]).append(d[f]['name'])
    
    for run in runs:
        for sample in runs[run]:
            print(run,sample,len(runs[run][sample]))

    return runs

def writeOutputs(runs,output,bucket): 
    # write into runs folder
    for run in runs:
        with open('{0}/runs/{1}.csv'.format(output,run),'wt') as outrf:
            for sample in runs[run]:
                with open('{0}/samples/{1}.csv'.format(output,sample),'wt') as outsf:
                    for f in runs[run][sample]:
                        outsf.write('{0},{1},{2}\n'.format(sample,bucket,f))
                        outrf.write('{0},{1},{2}\n'.format(sample,bucket,f))
      
def run(opts):
    files=getFiles(opts.bucket, opts.user, opts.keyfile)
    runs=groupFiles(files)
    writeOutputs(runs,opts.outdir,opts.bucket)

if __name__ == "__main__":
    # args
    parser = ArgumentParser(description='Create CSV files from OCI object store fastq files')
    parser.add_argument('-o', '--outdir', required=True,
                       help='output directory')
    parser.add_argument('-bn', '--bucket', required=False,default='test_nanopore_samples',
                       help='bucket name, default=test_nanopore_samples')
    parser.add_argument('-u', '--user', required=False,default='ocid1.user.oc1..aaaaaaaaavnaohgvyjwnvmkiigjnpiolola2zhamt7npvurn3vlxb55rfjqa',
                       help='user')
    parser.add_argument('-k', '--keyfile', required=False,default='/home/ubuntu/.oci/oci_api_key.pem',
                       help='output directory')

    opts, unknown_args = parser.parse_known_args()
    run(opts)


