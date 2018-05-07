from redis import Redis

redis = Redis()

import time
from functools import update_wrapper
from flask import request, g
from flask import Flask, jsonify

from models import Base, Item
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

import json

engine = create_engine('sqlite:///bargainMart.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
app = Flask(__name__)


# ADD RATE LIMITING CODE HERE
class RateLimit(object):
	expiration_window = 10  # give key extra 10s to expire in redis so that

	# badly sync clocks b/w worker and redis server
	#  do not cause any problems
	def __init__(self, key_prefix, limit, per, send_x_headers):
		# timestamp to indicate when a request limit can reset itself then
		# append this to my key
		self.reset = (int(time.time()) // per) * per + per
		# key(string) used to keep track of rate limit from each of d
		# requests
		self.key = key_prefix + str(self.reset)
		# limit and per defines no. of requests allowed over a time period.
		self.limit = limit
		self.per = per
		# send_x_header(boolean option) allows to inject to each response
		# header the no. of remaining requests a client can make before
		# they hit the limit
		self.send_x_headers  = send_x_headers
		# use pipeline to ensure we never increment a key without also
		# setting the key expiration in case exception happens b/w those lines
		# ex: if a process is killed
		p = redis.pipeline()
		# now increment the value of pipeline
		p.incr(self.key)
		# & set it to expire based on the reset value and expiration window
		p.expireat(self.key, self.reset + self.expiration_window)
		self.current = min(p.execute()[0], limit)

	# remaining request i have left
	remaining = property(lambda x: x.limit - x.current)
	# returns true if client hit their rate limit
	over_limit = property(lambda x: x.current >= x.limit)


@app.route('/rate-limited')
def index():
	return jsonify(
		{'response': 'This is a Rate limited response'}
	)


@app.route('/catalog')
def getCatalog():
	items = session.query(Item).all()

	# Populate an empty database
	if items == []:
		item1 = Item(name="Pineapple",
					 price="$2.50",
					 picture="https://upload.wikimedia.org/wikipedia/commons/c/cb/Pineapple_and_cross_section.jpg",
					 description="Organically Grown in Hawai'i")
		session.add(item1)
		item2 = Item(name="Carrots",
					 price="$1.99",
					 picture="http://media.mercola.com/assets/images/food-facts/carrot-fb.jpg",
					 description="High in Vitamin A")
		session.add(item2)
		item3 = Item(name="Aluminum Foil",
					 price="$3.50",
					 picture="http://images.wisegeek.com/aluminum-foil.jpg",
					 description="300 feet long")
		session.add(item3)
		item4 = Item(name="Eggs",
					 price="$2.00",
					 picture="http://whatsyourdeal.com/grocery-coupons/wp-content/uploads/2015/01/eggs.png",
					 description="Farm Fresh Organic Eggs")
		session.add(item4)
		item5 = Item(name="Bananas",
					 price="$2.15",
					 picture="http://dreamatico.com/data_images/banana/banana-3.jpg",
					 description="Fresh, delicious, and full of potassium")
		session.add(item5)
		session.commit()
		items = session.query(Item).all()
	return jsonify(catalog=[i.serialize for i in items])


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
