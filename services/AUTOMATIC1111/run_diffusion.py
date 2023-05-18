import webuiapi
import os
import random
import sys
from PIL import Image
import boto3
import datetime
from datetime import timedelta
from botocore.exceptions import NoCredentialsError


def get_images_from_s3(bucket_name, s3_folder, local_folder, min_size_kb):
  print(bucket_name, s3_folder, local_folder, min_size_kb)
  image_files = []
  s3 = boto3.client('s3')
  today = datetime.datetime.now()
  last_monday = today - timedelta(days=today.weekday())
  week = last_monday.strftime('%Y-%m-%d')

  print(f'week: {week}')
  try:
    print(f'Prefix: {s3_folder + week + "/images/"}')  
    s3_objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_folder + week + "/images/")

    if 'Contents' not in s3_objects:
      print('No objects found in the S3 bucket path.')
      return

    for object in s3_objects['Contents']:
      file_path = object['Key']
      filename = object['Key'].rsplit('/', 1)[-1]  # Extract the filename from the S3 object key
      if filename:  # Skip directories
        if filename.endswith(('.png', '.jpg', '.jpeg')):
          response = s3.head_object(Bucket=bucket_name, Key=file_path)
          print(response['ContentLength'])
          if response['ContentLength'] > min_size_kb * 1024:  # size in bytes
            image_files.append(file_path)
            # s3.download_file(bucket_name, object['Key'], local_filename)
            # print(f'Downloaded {filename} from S3 bucket {bucket_name}.')

    if not image_files:
      print(f'No images found in {s3_folder + week + "/"}')
      return None

  except NoCredentialsError:
    print('No AWS credentials found.')
    return

  random_file = random.choice(image_files)
  filename = random_file.rsplit("/", 1)[-1]
  print(f'Save image to {filename}')
  s3.download_file(bucket_name, random_file, f'./{filename}')
  return filename

bucket_name = 'medieval-news-press'
s3_folder = 'articles/'
local_folder = 'saved/'
min_size_kb = 30
print('Checking bucket...')
selected_image = get_images_from_s3(bucket_name, s3_folder, local_folder, min_size_kb)

if selected_image is None:
    print("No suitable image files found.")
    sys.exit()
else:
    print('Opening...')
    img = Image.open('./' + selected_image)

# create API client
api = webuiapi.WebUIApi()

print('Connecting to SD...')
# create API client with custom host, port
api = webuiapi.WebUIApi(host='0.0.0.0',
                        port=7860,
                        sampler='Euler a',
                        steps=20)
#

pos_prompt = "in the style of <lora:medieval_nocap_14repeats_v5-000019:1.1> (ohnx medieval)," \
             "drawing, painting, colorful"

negative_prompt = "deformed, bad anatomy, disfigured, poorly drawn face, mutation, mutated, extra limb," \
                " ugly, disgusting, poorly drawn hands, missing limb, floating limbs," \
                " disconnected limbs, malformed hands, blurry, ((((mutated hands and fingers)))), " \
                "watermark, watermarked, oversaturated, censored," \
                "distorted hands, amputation, missing hands, obese, doubled face, double hands"

print('Running interrogation...')
result = (api.interrogate(img))
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
result.image.save("test_image.jpg")
