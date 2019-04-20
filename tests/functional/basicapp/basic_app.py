from chili_pepper.app import ChiliPepper

app = ChiliPepper(app_name="demo", bucket_name="foobar", runtime="python3.7")


@app.task()
def say_hello(event, context):
    print("Hello world!")
