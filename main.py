# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask
from flask_reggie import Reggie
from flask import request
# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)

Reggie(app)
app.debug = True
app.secret_key = 'development key'

@app.route('/<regex(".*"):str>', methods=["GET", "POST", "PUT"])
def hello_world(str):
	data = {
		"path": str,
		"body": request.json if request.data else ""
	}
	print(data)
	return {
		"path": str,
		"body": request.json if request.data else ""
	}

# main driver function
if __name__ == '__main__':

	# run() method of Flask class runs the application
	# on the local development server.
	app.run(debug=True, host='51.250.9.36', port=5000)
