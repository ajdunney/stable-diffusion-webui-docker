import time
import webuiapi
import os
import random
import sys
from PIL import Image
import boto3
import datetime
from datetime import timedelta
from botocore.exceptions import NoCredentialsError


def get_images_from_s3(bucket_name, s3_folder, min_size_kb):
  print(bucket_name, s3_folder, min_size_kb)
  image_files = []
  s3 = boto3.client('s3')
  today = datetime.datetime.now().strftime('%Y-%m-%d')

  print(f'today: {today}')
  try:
    print(f'Prefix: {s3_folder + today + "/images/"}')
    s3_objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_folder + today + "/images/")

    if 'Contents' not in s3_objects:
      print('No objects found in the S3 bucket path.')
      return

    for object in s3_objects['Contents']:
      file_path = object['Key']
      filename = object['Key'].rsplit('/', 1)[-1]  # Extract the filename from the S3 object key
      if filename:  # Skip directories
        if filename.endswith(('.png', '.jpg', '.jpeg')):
          response = s3.head_object(Bucket=bucket_name, Key=file_path)
          if response['ContentLength'] > min_size_kb * 1024:  # size in bytes
            image_files.append(file_path)

    if not image_files:
      print(f'No images found in {s3_folder + today + "/"}')
      return None

  except NoCredentialsError:
    print('No AWS credentials found.')

  random_file = random.choice(image_files)
  filename = random_file.rsplit("/", 1)[-1]
  print(f'Save image to {filename}')
  s3.download_file(bucket_name, random_file, f'./{filename}')
  return filename


def upload_image_to_s3(bucket_name, file_name, s3_folder):
  print(bucket_name, s3_folder)
  s3 = boto3.client('s3')
  today = datetime.datetime.now().strftime('%Y-%m-%d')
  print(f'date: {today}')
  day_folder = os.path.join(s3_folder, today)
  print(f'date folder: {day_folder}')

  try:
    s3_objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=day_folder)
    if 'Contents' not in s3_objects:
      print('No objects found in the S3 bucket path. Creating directory.')
      s3.put_object(Bucket=bucket_name, Key=day_folder)
      print('Folder created')

    print(f'Uploading {file_name} to {bucket_name}, as {os.path.join(day_folder, file_name)}')
    s3.upload_file(file_name, bucket_name, os.path.join(day_folder, file_name))
    print('Upload complete')
  except NoCredentialsError:
    print('No AWS credentials found.')
    return
  return


print('Connecting to SD...')
# create API client with custom host, port
api = webuiapi.WebUIApi(host='0.0.0.0',
                        port=7860,
                        sampler='Euler a',
                        steps=20)

bucket_name = 'medieval-news-press'
IMAGES_TO_PROCESS = 5

for i in range(IMAGES_TO_PROCESS):
  print(f'Loop {i}/{IMAGES_TO_PROCESS}')
  print('Checking bucket...')
  selected_image = get_images_from_s3(bucket_name, s3_folder='articles/', min_size_kb=30)

  if selected_image is None:
    print("No suitable image files found.")
    sys.exit()
  else:
    print('Opening...')
    img = Image.open('./' + selected_image)

  api.util_wait_for_ready(check_interval=5.0)

  pos_prompt = "in the style of <lora:medieval_nocap_14repeats_v5-000019:1.1> (ohnx medieval)," \
               "drawing, painting, colorful"

  negative_prompt = "deformed, bad anatomy, disfigured, poorly drawn face, mutation, mutated, extra limb," \
                    " ugly, disgusting, poorly drawn hands, missing limb, floating limbs," \
                    " disconnected limbs, malformed hands, blurry, ((((mutated hands and fingers)))), " \
                    "watermark, watermarked, oversaturated, censored," \
                    "distorted hands, amputation, missing hands, obese, doubled face, double hands"

  print('Running interrogation...')
  result = (api.interrogate(img))
  api.util_wait_for_ready(check_interval=5.0)
  print(result.info)
  pos_prompt = result.info.split(',')[0] + ', ' + pos_prompt
  print(pos_prompt)

  print('Running generation')
  result = api.img2img(prompt=pos_prompt,
                       negative_prompt=negative_prompt,
                       images=[img],
                       width=512,
                       height=512,
                       sampler_name="Euler a",
                       cfg_scale=7,
                       seed=1231,
                       denoising_strength=6.5
                       )

  print('Generation complete, save locally')
  result.image.save(f"./{selected_image}")
  print(f'Saved {selected_image}. Uploading to S3')
  upload_image_to_s3(bucket_name=bucket_name, file_name=selected_image, s3_folder='outputs/')
