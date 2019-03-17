import json
import os
import sys
import requests
import boto3
from io import BytesIO

ACCESS_KEY_ID = os.environ['aws_access_key_id']
SECRET_ACCESS_KEY = os.environ['aws_secret_access_key']
BUCKET_NAME = os.environ['bucket_name']
NIP = os.environ['NIP']
NPORT = int(os.environ['NPORT'])

def getfile(filename, destination):
    res = requests.get(url='http://'+ NIP + ':' + str(NPORT) + '/api/v1/readfile?file=' + filename + '')
    if not res:
        print("404: file not found")
        return
    fileinfo = res.json()
    print(fileinfo)
    #filetype = fileinfo['filetype']
    with open(destination, 'wb') as fd:
        for f in fileinfo['block_info']:
            nodes = f[1]
            for n in nodes:
                url = 'http://' + n + '/readfile?block=' + f[0]
                res = requests.get(url=url, stream=True)
                if res:
                    fd.write(res.raw.read())
                    break
                else:
                    print("No blocks found. Possibly a corrupt file")

# Read file from S3, return data
def readS3file(file):
    s3 = boto3.resource(
      's3',
      #region_name='us-west-2',
      aws_access_key_id=ACCESS_KEY_ID,
      aws_secret_access_key=SECRET_ACCESS_KEY
    )
    obj = s3.Object(BUCKET_NAME, file)
    data = obj.get()['Body'].read()
    return data


# Write data from S3 to new file
def putS3file(args):
    try: 
        filename = args[1]
        filetype = args[2]
        
        # Data from S3
        data = readS3file(filename)
        size = len(data)
        blocks = getBlocks(filename, str(size), filetype)
        blocksize = getBlockSize()

        # Write data from S3 into file
        binary_stream = BytesIO(bytes(data))
        for b in blocks:
           datablock = binary_stream.read(blocksize)
           block_id = b[0]
           payload = {'blockId': block_id}
           multipart_form_data = {
              'fileData': ('None', datablock),
              'filter': (None, json.dumps(payload))
           }
           for n in b[1]:
              url = 'http://' + n + '/upload'
              print(url)
              response = requests.post(url, files=multipart_form_data)
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
        with open(source, 'rb') as f:
            for b in blocks:
                print("block as b"+str(b))
                data = f.read(blocksize)
                block_id = b[0]
                payload = {'blockId': block_id}
                multipart_form_data = {
                    'fileData': ('None', data),
                    'filter': (None, json.dumps(payload)) # not able to serialise the bytes into json object hence need to dump into json string
                }
                for n in b[1]:
                    url = 'http://' + n + '/upload'
                    print(url)
                    response = requests.post(url, files=multipart_form_data)
                    print(response.status_code)
    except Exception as error:
        print(error)

def getBlocks(filename, size, filetype):
    r = requests.get(url='http://'+ NIP + ':' + str(NPORT) + '/api/v1/getblock?file=' + filename + '&size=' + str(size) + '&filetype=' + filetype)
    if r.status_code != 200:
        raise Exception(r.text)
    blocks = r.json()
    return blocks


def getBlockSize():
    r = requests.get(url='http://'+ NIP + ':' + str(NPORT) + '/api/v1/getblocksize')
    block_size = int(r.json())
    return block_size


def getDataNodes():
    r = requests.get(url='http://'+ NIP + ':' + str(NPORT) + '/api/v1/getdatanodes')
    datanodes = r.json()
    return datanodes


def main(args):
    if args[0] == "getfile":
        getfile(args[1], args[2])
    elif args[0] == "putfile":
        putfile(args)
    elif args[0] == "putS3file":
        putS3file(args)
    else:
        print("try 'put srcFile destFile OR get file'")


if __name__ == "__main__":
    main(sys.argv[1:])
