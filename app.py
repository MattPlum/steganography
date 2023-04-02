from flask import Flask, render_template, request, send_file
from PIL import Image
import openai
import requests
import secrets
import string
import config 

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('index.html')

# Generate encoded image
@app.route('/generate', methods=['POST'])
def generate():
    # Get the prompt from the user
    prompt = request.form.get('prompt')

    # Generate an image from the prompt using OpenAI API
    openai.api_key = config.OPENAI_API_KEY

    # Create an OpenAI DALL-E image
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="256x256",
        response_format="url"
    )

    # Get the URL of the image generated from the API 
    image_url = response['data'][0]['url']

    # Load the image from the URL
    image_data = Image.open(requests.get(image_url, stream=True).raw)

    # Convert the image to RGB mode
    image_data = image_data.convert("RGB")
    original_image = image_data.save("static/original_image.png")
    
    # Get the secret message from the user and convert to binary format
    secret_message = request.form.get('secret_message')
    enc_method = request.form.get('encryption_method')
    width, height = image_data.size
    
    if(enc_method == "none"):
        binary_message = ''.join(format(ord(i), '08b') for i in secret_message)
    elif enc_method == "caesar":
        # Apply the Caesar cipher with a shift of 3
        ciphertext = caesar_cipher(secret_message, 3)
        binary_message = ''.join(format(ord(i), '08b') for i in ciphertext)
        # Get the size of the image
    elif enc_method == "vigenere":
        # Apply the Vigenère cipher with a key of "secret"
        ciphertext = vigenere_cipher(secret_message, "secret")
        binary_message = ''.join(format(ord(i), '08b') for i in ciphertext)
        
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
    encoded_image.save('static/encoded_image.png')

    return render_template('result.html', image_url=image_url)

def caesar_cipher(plaintext, shift):
        alphabet = string.ascii_lowercase
        shifted_alphabet = alphabet[shift:] + alphabet[:shift]
        table = str.maketrans(alphabet, shifted_alphabet)
        return plaintext.translate(table)

# Define the Vigenère cipher function
def vigenere_cipher(plaintext, key):
    key = key.lower()
    plaintext = plaintext.lower()
    key_len = len(key)
    key_as_int = [ord(i) - ord('a') for i in key]
    plaintext_int = [ord(i) - ord('a') for i in plaintext]
    ciphertext = ''
    for i in range(len(plaintext_int)):
        value = (plaintext_int[i] + key_as_int[i % key_len]) % 26
        ciphertext += chr(value + ord('a'))
    return ciphertext

def decode_message(image_file):
    # Load the encoded image
    encoded_image = Image.open(image_file)

    # Get the size of the image
    width, height = encoded_image.size

    # Initialize the binary message variable
    binary_message = ''

    # Iterate over each pixel of the encoded image in row-major order
    print("Decoding...")
    for y in range(height):
        for x in range(width):
            # Get the RGB values of the current pixel
            r, g, b = encoded_image.getpixel((x, y))

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

    # Return the decoded message
    return message

def binary_to_text(binary_str):
    # Split the binary string into 8-bit chunks
    chunks = [binary_str[i:i+8] for i in range(0, len(binary_str), 8)]

    # Convert each chunk to its corresponding ASCII character
    text = ''.join([chr(int(chunk, 2)) for chunk in chunks])

    return text

@app.route('/decode_image', methods=['POST'])
def decode_image():
    # Get the uploaded image file from the request object
    encoded_image = request.files['encoded_image']

    # Decode the secret message from the image
    secret_message = decode_message(encoded_image)

    # Render the decoded message in the template
    return render_template('decode.html', message=secret_message)

@app.route('/download_encoded_image')
def download_encoded_image():
    return send_file('static/encoded_image.png', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
