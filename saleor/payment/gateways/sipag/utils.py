import tempfile


def create_cert_temp_file(content: str):
    cert = tempfile.NamedTemporaryFile(delete=False)
    cert.write(str.encode(content))
    cert.close()
    return cert


def generate_cert_files(client_cert: str, client_pkey: str):
    client_cert_file = create_cert_temp_file(client_cert)
    client_key_file = create_cert_temp_file(client_pkey)
    return client_cert_file.name, client_key_file.name
