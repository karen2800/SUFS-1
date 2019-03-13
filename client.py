import os
import sys
import requests
from io import BytesIO

ACCESS_KEY_ID = os.environ['aws_access_key_id']
SECRET_ACCESS_KEY = os.environ['aws_secret_access_key']
BUCKET_NAME = os.environ['bucket_name']


def getfile(filename, destination):
    res = requests.get(url='http://127.0.0.1:9000/api/v1/readfile?file=' + filename + '')
    if not res:
        print("404: file not found")
        return
    fileinfo = res.json()
    print(res.text)
    filetype = fileinfo['filetype']
    #datanodes = getDataNodes()
    with open(destination, 'w') as fd:
        for f in fileinfo['block_info']:
            nodes = f[1]
            for n in nodes:
                url = 'http://' + n + '/readfile?block=' + f[0]
                res = requests.get(url=url)
                if res:
                    fd.write(res.text)
                    break
                else:
                    print("No blocks found. Possibly a corrupt file")

# Read file from S3, return data
def readS3file(file):
    s3 = boto3.resource(
      's3',
      region_name='us-west-2',
      aws_access_key_id=ACCESS_KEY_ID,
      aws_secret_access_key=SECRET_ACCESS_KEY
    )
    obj = s3.Object(BUCKET_NAME, file)
    data = obj.get()['Body'].read()
    return data


# Write data from S3 to file
def putS3file(args):
    try: 
        # Data from S3
        data = readS3file(filename)

        source = args[1]
        filename = args[2]
        filetype = args[3]

        size = len(data)
        blocks = getBlocks(filename, str(size))
        blocksize = getBlockSize()
        print("check block size " + str(blocksize))
        datanodes = getDataNodes()

        # Write data from S3 into file
        binary_stream = BytesIO(bytes(data))
        for b in blocks:
           datablock = binary_stream.read(blocksize)
           block_id = b[0]
           nodes = [datanodes[_] for _ in b[1]]
           multipart_form_data = {
              'fileData': datablock,
              'blockId': block_id
           }
           for n in nodes:
              url = 'http://' + n[0] + ':' + n[1] + '/upload'
              print(url)
              response = requests.post(url, json=multipart_form_data)
              print(response.status_code)
    except Exception as error:
        print(error)
        

def putfile(args):
    try:
        source = args[1]
        filename = args[2]
        filetype = args[3]
        size = os.path.getsize(source)
        blocks = getBlocks(filename, str(size), filetype)
        print(blocks)
        blocksize = getBlockSize()
        print("check block size "+str(blocksize))
        with open(source) as f:
            for b in blocks:
                print("block as b"+str(b))
                data = f.read(blocksize)
                block_id = b[0]
                multipart_form_data = {
                    'fileData': data,
                    'blockId': block_id
                }
                for n in b[1]:
                    url = 'http://' + n + '/upload'
                    print(url)
                    response = requests.post(url, json=multipart_form_data)
                    print(response.status_code)
    except Exception as error:
        print(error)

def getBlocks(filename, size, filetype):
    r = requests.get(url='http://127.0.0.1:9000/api/v1/getblock?file=' + filename + '&size=' + str(size) + '&filetype=' + filetype)
    if r.status_code != 200:
        raise Exception(r.text)
    blocks = r.json()
    return blocks


def getBlockSize():
    r = requests.get(url='http://127.0.0.1:9000/api/v1/getblocksize')
    block_size = int(r.json())
    return block_size


def getDataNodes():
    r = requests.get(url='http://127.0.0.1:9000/api/v1/getdatanodes')
    datanodes = r.json()
    return datanodes

def update_replica():
    print("REPLICA=")
    multipart_form_data = {
        'destinationNode': '127.0.0.1:5002',
        'blockId': '5753305c-4566-11e9-a12a-8c8590872aa0'
    }
    response = requests.post(url='http://127.0.0.1:5001/replica', json=multipart_form_data)
    if response.status_code != 200:
        raise Exception(response.text)


def main(args):
    if args[0] == "getfile":
        getfile(args[1], args[2])
    elif args[0] == "putfile":
        putfile(args)
    else:
        print("try 'put srcFile destFile OR get file'")


if __name__ == "__main__":
    main(sys.argv[1:])
