import argparse
import logging
import sys
from cryptography.fernet import Fernet

def encrypt_file(input_file: str, key: str = None):
    # Generate a key
    if key is None:
        key = Fernet.generate_key()
    else:
        key = key.encode()

    # Create a Fernet object
    cipher_suite = Fernet(key)

    # Read the contents of the file to encrypt
    with open(input_file, 'rb') as file:
        file_data = file.read()

    # Encrypt the file data
    encrypted_data = cipher_suite.encrypt(file_data)

    # Write the encrypted data to a new file
    with open(input_file + '.encrypt', 'wb') as file:
        file.write(encrypted_data)


    print(f"Encrypted {input_file} to {input_file}.encrypt with key: '{key.decode()}'")

def decrypt_file(input_file: str, key: str):
    output_file = input_file.replace('.encrypt', '')
    if output_file == input_file:
        raise Exception("Input file must have a .encrypt extension: {input_file}")

    # Create a Fernet object
    cipher_suite = Fernet(key.encode())

    # Read the contents of the file to decrypt
    with open(input_file, 'rb') as file:
        file_data = file.read()

    # Decrypt the file data
    decrypted_data = cipher_suite.decrypt(file_data)

    # Write the decrypted data to a new file
    with open(output_file, 'wb') as file:
        file.write(decrypted_data)

    print(f"Decrypted {input_file} to {output_file}.decrypt with key: '{key}'")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    parser = argparse.ArgumentParser(description='encrypts a file and outpus the key')
    parser.add_argument('--input_file', type=str, help='Input file to encrypt', required=True)
    parser.add_argument('--decode', action='store_true', help='If set, will decode the file instead of encoding it')
    parser.add_argument('--key', type=str, help='Key to use to encode/decode the file. Must be set for decode. For encode a new key will be generated if not set')
    args = parser.parse_args()
    if args.decode:
        if args.key is None:
            raise Exception("Key must be set for decode")
        decrypt_file(args.input_file, args.key)
    else:
        encrypt_file(args.input_file, args.key)
