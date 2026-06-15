import urllib.request
try:
    req = urllib.request.Request(
        'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEisSaRg9e6Kt9lPEq7pH8-F4RIKOoZ9HT4G91aXFVwzdySq9HURQdcU6G6j1icFgmD7Wj3RkLo01fijv-dfXY5Qfs22mmQArnT-POo_4Pl8Y1D_nhH_-A5hN55Vfvg5atJ03hyDUXvxG4ADHDFpzhna2IehbwVuSQkQpNLj_w8vNL9aTC-LwMBzEvm5/w1200-h630-p-k-no-nu/National%20Institute%20of%20Technology%20Andhra%20Pradesh.png',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response:
        with open('static/nitap_logo.png', 'wb') as out_file:
            out_file.write(response.read())
    print("Logo downloaded successfully from blogger")
except Exception as e:
    print(f"Error: {e}")
