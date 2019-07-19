import csv
import os
import shutil
from zipfile import ZipFile

def create_zip(curr_path, zip_name):
    os.chdir(curr_path)
    files = os.listdir(curr_path)
    zipObj = ZipFile(zip_name, 'w')
    for f in files:
        zipObj.write(f)
    zipObj.close()


def read_csv_as_dict_list(file_to_read, headers):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = [l for l in csv.DictReader(f, headers) if l]
        for line in reader:
            dict_list.append(line)
    return dict_list


def format_date(year, month):
    return '-'.join([year, month.zfill(2)])


def write_to_csv(folder_full_path, filename, data):
    os.chdir(folder_full_path)
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, dialect="excel").writerows(data)


def delete_folder(path,name):
    os.chdir(path)
    shutil.rmtree(name)