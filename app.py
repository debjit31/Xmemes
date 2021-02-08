from flask import Flask, render_template,request,redirect,url_for,flash,jsonify
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import psycopg2
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

app = Flask(__name__)
app.secret_key = 'njhdhsrh748365badjf'
## POSTGRES DB INTEGRATION
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
##app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

class Memepost(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    author = db.Column(db.String(50))
    caption = db.Column(db.String(100))
    image_link = db.Column(db.String(500),unique = True)
    date_posted = db.Column(db.Text)
    def __init__(self, author, caption, image_link, date_posted):
        self.author = author
        self.caption = caption
        self.image_link = image_link
        self.date_posted = date_posted.strftime("%d/%m/%Y %H:%M:%S")

## Schema to serialize ORM objects 
## using marshmallow and convert them to json responses
class PostSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Memepost

# route handling get and post requests for posts and returning a json response
@app.route('/memes',methods=["POST","GET"])
def get_memes_by_api():
    ## POST curl requests
    if request.method == "POST":
        data = request.json
        author = data['name']
        caption = data['caption']
        url = data['url']
        post = Memepost(author,caption,url,datetime.now())
        try:
            db.session.add(post)
            db.session.commit()
            return jsonify({"id" : post.id})
        except IntegrityError:
            return jsonify({"error" : "This meme was already submitted."})
    else:
        ## GET curl requests
        all_posts = Memepost.query.order_by(Memepost.id.desc()).limit(100).all()
        post_schema = PostSchema(many=True)
        output = post_schema.dump(all_posts)
        return jsonify(output)

@app.route('/delete_meme/<int:id>')
def delete(id):
    post = Memepost.query.filter_by(id = id).one()
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('memes'))

@app.route('/update_meme/<int:post_id>',methods=['GET'])
def update_a_meme(post_id):
    meme = Memepost.query.filter_by(id = post_id).one()
    return render_template('layouts/update_posts.html', post = meme)

@app.route('/patch_meme/<int:post_id>', methods = ["POST"])
def update_meme(post_id):
    if request.method == "POST":
        name = request.form['name']
        caption = request.form['caption']
        url = request.form['meme-url']
        
        meme = Memepost.query.filter_by(id = post_id).one()
        meme.author = name 
        meme.caption = caption
        meme.image_link = url
        meme.date_posted = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        db.session.commit()
        return redirect(url_for('view_a_meme', post_id=meme.id))

## route handling get request for specific memes and returning a json response
@app.route('/memes/<int:post_id>',methods = ['GET','PATCH'])
def view_a_meme_by_api(post_id):
    if request.method == "GET":
        try:
            meme = Memepost.query.filter_by(id = post_id).one()
            meme_schema = PostSchema()
            output = meme_schema.dump(meme)
            return jsonify(output)
        except NoResultFound:
            return jsonify({"error" : "Record does not exist."})
    else:
        target_meme = Memepost.query.filter_by(id = post_id).one()
        target_meme.date_posted = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data = request.json
        try:
            caption = data['caption']
            target_meme.caption = caption
        except KeyError:
            pass
        try:
            url = data['url']
            target_meme.image_link = url
        except KeyError:
            pass             
        db.session.commit()

        return jsonify({'status' : 'Updated'})


@app.route('/',methods = ['POST','GET'])
## Handling POST and GET requests through browser rendering
def memes():
    ## Handling POST requests
    if request.method == 'POST':
        author = request.form['name']
        caption = request.form['caption']
        url = request.form['meme-url']

        post = Memepost(author,caption,url,datetime.now())

        try:
            db.session.add(post)
            db.session.commit()
        except IntegrityError:
            flash('This meme has already been submitted!!')
            db.session.rollback()
        all_posts = Memepost.query.order_by(Memepost.id.desc()).limit(100).all()
    else:
        ## Handling GET requests
        all_posts = Memepost.query.order_by(Memepost.id.desc()).limit(100).all()
    return render_template('layouts/home.html',posts = all_posts)
        
@app.route('/meme/<int:post_id>',methods = ["GET"])
## viewing a particular meme through browser
## memes are queried from db using id column which is a primary key
def view_a_meme(post_id):
    try:
        meme = Memepost.query.filter_by(id = post_id).one()
        return render_template('layouts/post.html', post = meme)
    except NoResultFound:
        return render_template('errors/custom_records_not_found.html'), 404
        
@app.errorhandler(404)
def page_not_found(error):
	return render_template('errors/custom_404_error.html'), 404

if __name__ == "__main__":
    app.run()

