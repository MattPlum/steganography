import openai
from PIL import Image  # Import the Pillow package for image processing
import requests

# Set up the OpenAI API client
openai.api_key = "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"
prompt = input("Enter image to encode :")

# Create an OpenAI DALL-E image
response = openai.Image.create(
    prompt=prompt,
    n=1,
    size="1024x1024",
    response_format="url"
)
image_url = response['data'][0]['url']

# Load the image from the URL
image_data = Image.open(requests.get(image_url, stream=True).raw)

# Convert the image to RGB mode
image_data = image_data.convert("RGB")
image_data.save("original_image.png")

# Get the secret message from the user and convert to binary format
secret_message = input("Enter a secret message : ")
binary_message = ''.join(format(ord(i), '08b') for i in secret_message)

# Get the size of the image
width, height = image_data.size

# Check if the binary message can fit in the image
if len(binary_message) > width * height * 3:
    raise ValueError("Message is too long to encode in the image")

# Add padding to the binary message to fill the remaining bits in the image
binary_message += "0" * (width * height * 3 - len(binary_message))

# Initialize a new image for the encoded message
encoded_image = Image.new('RGB', (width, height), (0, 0, 0))

# Iterate over each pixel of the image in row-major order
bit_index = 0
for y in range(height):
    for x in range(width):
        # Get the RGB values of the current pixel
        r, g, b = image_data.getpixel((x, y))

        # If there are more bits in the message, modify the least significant bit of each color channel
        if bit_index < len(binary_message):
            # Red channel
            bit = int(binary_message[bit_index])
            r = (r & 0xfe) | bit
            # print(format(r,'b'))
            bit_index += 1

            # Green channel
            bit = int(binary_message[bit_index])
            g = (g & 0xfe) | bit
            bit_index += 1

            # Blue channel
            bit = int(binary_message[bit_index])
            b = (b & 0xfe) | bit
            bit_index += 1

        # Create a new pixel with the modified red, green, and blue values
        encoded_pixel = (r, g, b)

        # Set the pixel in the new image
        encoded_image.putpixel((x, y), encoded_pixel)

# Save the encoded image
encoded_image.save("encoded_image.png")

# Load the encoded image
encoded_image_data = Image.open("encoded_image.png")

# Get the size of the encoded image
width, height = encoded_image_data.size

# Initialize a variable to hold the binary message
binary_message = ""

# Iterate over each pixel of the encoded image in row-major order
for y in range(height):
    for x in range(width):
        # Get the RGB values of the current pixel
        r, g, b = encoded_image_data.getpixel((x, y))

        # Append the least significant bit of each color channel to the binary message
        binary_message += str(r & 1)
        binary_message += str(g & 1)
        binary_message += str(b & 1)

binary_message = binary_message.rstrip("0")

# Convert the binary message to ASCII
message = ""
for i in range(0, len(binary_message), 8):
    byte = binary_message[i:i+8]
    message += chr(int(byte, 2))
    
print(message)