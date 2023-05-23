from flask import Flask, render_template, request, send_file
from PIL import Image
import openai
import requests
import secrets
import string
import config 
from io import BytesIO

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Get the prompt, either AI image or user uploaded image
    if request.form['prompt'] != "":
        prompt = request.form['prompt']

        # Set the api key from the configuration file
        openai.api_key = config.OPENAI_API_KEY

        # Create an OpenAI DALL-E image
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256",
            response_format="url"
        )

        # Get the URL of the image generated 
        image_url = response['data'][0]['url']

        # Load the image from the URL
        image_data = Image.open(requests.get(image_url, stream=True).raw)
        original_image = image_data.save("static/original_image.png")
    else:
        user_image = request.files['user_image']
        image_data = Image.open(BytesIO(user_image.read()))

    # Convert the image to RGB and save
    image_data = image_data.convert("RGB")
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

    # Make a new image for the encoded message
    encoded_image = Image.new('RGB', (width, height), (0, 0, 0))

    # Iterate over each pixel of the image
    bit_index = 0
    for y in range(height):
        for x in range(width):
            # Get the RGB values of the current pixel
            r, g, b = image_data.getpixel((x, y))

            # Check if there are more bits to replace
            if bit_index < len(binary_message):
                # Red
                bit = int(binary_message[bit_index])
                r = (r & 0xfe) | bit
                bit_index += 1

                # Green
                bit = int(binary_message[bit_index])
                g = (g & 0xfe) | bit
                bit_index += 1

                # Blue
                bit = int(binary_message[bit_index])
                b = (b & 0xfe) | bit
                bit_index += 1

            # Create a new pixel with the modified red, green, and blue values
            encoded_pixel = (r, g, b)

            # Put the pixel in the new image
            encoded_image.putpixel((x, y), encoded_pixel)

    # Save the encoded image
    encoded_image.save('static/encoded_image.png')

    # Render the result template HTML
    return render_template('result.html')

# Caesar Cipher function
def caesar_cipher(plaintext, shift):
        alphabet = string.ascii_lowercase
        shifted_alphabet = alphabet[shift:] + alphabet[:shift]
        table = str.maketrans(alphabet, shifted_alphabet)
        return plaintext.translate(table)

# Vigenere cipher function
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

# Convert binary to text
def binary_to_text(binary_str):
    # Split the binary string into 8-bits
    chunks = [binary_str[i:i+8] for i in range(0, len(binary_str), 8)]

    # Convert each 8-bit to its corresponding ASCII character
    text = ''.join([chr(int(chunk, 2)) for chunk in chunks])

    return text


@app.route('/decode_image', methods=['POST'])
def decode_image():
    # Get the uploaded file strip bits to get the encoded message
    encoded_image = request.files['encoded_image']
    encoded_message = decode_message(encoded_image)

    # Decrypt the message if Caesar Cipher was used        
    if request.form['encryption_method'] == 'caesar':
        decoded_message = caesar_decrypt(encoded_message, 3)
    elif request.form['encryption_method'] == 'vigenere':
        decoded_message = vigenere_decrypt(encoded_message, "secret")       
    else:
        decoded_message = encoded_message
    
    # Render the decoded message in the template
    return render_template('decode.html', message=decoded_message)


# Decode the message form the encoded image
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

    #binary_message = binary_message.rstrip("0")

    # Convert the binary message to ASCII
    message = ""
    for i in range(0, len(binary_message), 8):
        byte = binary_message[i:i+8]
        message += chr(int(byte, 2))

    # Return the decoded message
    return message

# Decryption method for a caesaer encrypted message
def caesar_decrypt(message, shift):
    decrypted_message = ""
    for letter in message:
        if letter.isalpha():
            new_letter_code = ord(letter) - shift
            if letter.isupper():
                if new_letter_code < ord('A'):
                    new_letter_code += 26
            elif letter.islower():
                if new_letter_code < ord('a'):
                    new_letter_code += 26
            decrypted_message += chr(new_letter_code)
        else:
            decrypted_message += letter
    return decrypted_message


# Decryption method for a vigenere encrypted message
def vigenere_decrypt(ciphertext, key):
    decrypted_message = ""
    key_length = len(key)
    key_index = 0

    for letter in ciphertext:
        if letter.isalpha():
            if letter.isupper():
                base = ord('A')
            else:
                base = ord('a')

            key_letter = key[key_index % key_length]

            shift = ord(key_letter) - base
            new_letter_code = ord(letter) - shift

            if letter.isupper():
                if new_letter_code < ord('A'):
                    new_letter_code += 26
            elif letter.islower():
                if new_letter_code < ord('a'):
                    new_letter_code += 26

            decrypted_message += chr(new_letter_code)
            key_index += 1
        else:
            decrypted_message += letter

    return decrypted_message

# Route for downloading the encoded image
@app.route('/download_encoded_image')
def download_encoded_image():
    return send_file('static/encoded_image.png', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
