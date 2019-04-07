from kale.app import Kale

app = Kale(app_name="demo", bucket_name="TODO", runtime="python3.7")


@app.task()
def say_hello():
    print("Hello world!")
