import os

nextcloudBase = "/srv/dev-disk-by-uuid-0901e9da-0191-4a3f-b7ff-d8cc98c9c617/16TB/.Cloud"
files = ["nextcloud.log", "flow.log"]
for f in files:
    for i in range(7, 0, -1):
        os.system("cp {}/{}_{} {}/{}_{}".format(nextcloudBase, i, f, nextcloudBase, i+1, f))
    os.system("cp {}/{} {}/1_{}".format(nextcloudBase, f, nextcloudBase, f))
    os.system("truncate {}/{} --size 0".format(nextcloudBase, f))