# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask
from werkzeug.routing import BaseConverter
from flask_reggie import Reggie
# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)

Reggie(app)
app.debug = True
app.secret_key = 'development key'

@app.route('/<regex(".*"):str>')
def hello_world(str):
	print(str)
	return 'Hello World'

# main driver function
if __name__ == '__main__':

	# run() method of Flask class runs the application
	# on the local development server.
	app.run()
