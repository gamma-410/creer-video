# CREER | @gamma_410
# Copyright 2022 gamma410.win

import os
from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import null
from werkzeug.security import generate_password_hash, check_password_hash
import boto3


# flaskアプリ のおまじない
app = Flask(__name__)


# データベースの作成 / 設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postData.db'
app.config['SECRET_KEY'] = '5730292743938474948439320285857603' #os.urandom(24)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# flask-login のおまじない
login_manager = LoginManager()
login_manager.init_app(app)


# (あまり理解してないから保留)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# SQLite の設定(動画投稿)
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    postUser = db.Column(db.String(20), nullable=False)
    postTitle = db.Column(db.String(20), nullable=False)
    postVideoDetail = db.Column(db.Text, nullable=False)
    videoUrl = db.Column(db.Text, nullable=False)
    imgUrl = db.Column(db.Text, nullable=False)


# SQLite の設定(ログイン)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    userdetail = db.Column(db.Text)
    useremail = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(25), nullable=False)


# S3 の設定
s3 = boto3.client('s3',
                  endpoint_url='https://ff33cdd7aff0f3c972f68f06c22b6408.r2.cloudflarestorage.com/creer',
                  aws_access_key_id='4e69ec09aa2f896c7d6f39a22d7caafb',
                  aws_secret_access_key='fd95bafb33b9579a072d9e75bc85193c3b2b4ca38e4545ca0f89b922e5f28243'
                  )

# バケット名を代入しておく
Bucket = 'creer'

# ルーター
@app.route('/')
def redirect_func():
    return redirect('/front')


@app.route('/front/welcome')
def welcome():
    return render_template('welcome.html')


@app.route('/front', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        posts = Post.query.order_by(Post.id.desc()).all()  # 学び: .order_by({DB名}.{テーブル名}.{ desc() または asc() }) とする !!
        return render_template('index.html', posts=posts)
    else:
     try:
        # テキスト関連は普通にSQLite用
        postUser = current_user.username
        # ログインユーザー名を取れる (current_user. + { DBで用意した id, username, password(ハッシュ値) が取れる })

        postTitle = request.form.get('postTitle')
        postVideoDetail = request.form.get('postVideoDetail')

        # 入力したタイトル + "拡張子" で保存する
        videoUrl = postTitle + ".mp4"
        imgUrl = postTitle + ".jpg"

        # 画像・動画 ファイル を 取得
        picture = request.files['imgUrl']
        video = request.files['videoUrl']

        imageMetaData = "image/jpeg"  # フォーマットの指定 (画像)
        videoMetaData = "video/mp4"  # フォーマットの指定 (動画)

        # S3 に アップロード （画像・動画 の保存は S3 に任せる）
        s3.upload_fileobj(picture, Bucket, f'picture/{imgUrl}', ExtraArgs={'ContentType': imageMetaData})
        s3.upload_fileobj(video, Bucket, f'video/{videoUrl}', ExtraArgs={'ContentType': videoMetaData})

        # DB にまとめて保存...!
        new_post = Post(postUser=postUser, postTitle=postTitle, postVideoDetail=postVideoDetail, videoUrl=videoUrl,
                        imgUrl=imgUrl)
        db.session.add(new_post)
        db.session.commit()
        flash("動画をアップロードできました!")
        
        return redirect('/front')
     except:
        
        flash("動画のアップロードに失敗しました...")
        return redirect('/front/studio') 
    

@app.route('/front/watch/<int:id>')
def watch(id):
    post = Post.query.get(id)
    return render_template('watch.html', post=post)


@app.route('/front/studio/create')
@login_required  # ログイン済みかをチェックする
def new():
    return render_template('new.html')


@app.route('/front/studio/manage')
@login_required  # ログイン済みかをチェックする
def manage():
    posts = Post.query.filter_by(postUser=current_user.username).order_by(Post.id.asc()).all()

    return render_template('manage.html', posts=posts)


@app.route('/front/studio/manage/delete/<int:id>')
@login_required  # ログイン済みかをチェックする
def delete(id):
    post = Post.query.get(id)

    s3.delete_object(Bucket=Bucket, Key=f'picture/{post.imgUrl}')
    s3.delete_object(Bucket=Bucket, Key=f'video/{post.videoUrl}')
    
    db.session.delete(post)
    db.session.commit()
    return redirect('/front/studio/manage')

# ---------- DEBUG 機能 ----------

@app.route('/front/user/debug', methods=['GET', 'POST'])
def manage1():
    users = User.query.order_by(User.id.asc()).all()

    return render_template('debug.html', users=users)


@app.route('/front/user/debug/delete/<int:id>', methods=['GET', 'POST'])
@login_required  # ログイン済みかをチェックする
def delete1(id):
    postData = Post.query.filter_by(id=id).first()
    user = User.query.get(id)

    db.session.delete(postData)
    db.session.delete(user)
    db.session.commit()

    return redirect('/front/user/debug')

# ---------- DEBUG 機能 (ここまで) ----------

@app.route('/front/user/<string:user>', methods=['GET', 'POST'])
def userPage(user):
    userCount = Post.query.filter_by(postUser=user).count()
    if userCount == 0:
        flash("まだ動画が投稿されていないのでプロフィールを表示できません...")
        return redirect('/front')
    else:
        userCount = Post.query.filter_by(postUser=user).count()
        posts = Post.query.filter_by(postUser=user).order_by(Post.id.desc()).all()
        userName = User.query.filter_by(username=user).first() ## 超絶適当に取得したwwww
        userIcon = Post.query.filter_by(postUser=user).first() ## つまり、最初のだけでいいから欲しいってわけよw

        return render_template('user.html', posts=posts, userName=userName, userIcon=userIcon, userCount=userCount)


@app.route('/front/user/edit_profile/<string:user>', methods=['GET', 'POST'])
@login_required
def editProfile(user):
    if request.method == "POST":
        try:
            usericon = request.files['userIcon']
            userdetail = request.form.get('postUserDetail')
            iconUrl = user + ".jpg"
            iconMetaData = "image/jpeg"  # フォーマット

            if usericon:
                s3.upload_fileobj(usericon, Bucket, f'users/{iconUrl}', ExtraArgs={'ContentType': iconMetaData})
            else:
                print("パス")

            if userdetail:
                userData = User.query.filter_by(username=user).first()
                userData.userdetail = userdetail
                db.session.merge(userData)
                db.session.commit()

            else:
                print("パス")

            flash("プロフィールを変更しました！（WEBブラウザのキャッシュにより、すぐにアイコンが変更されない場合があります。）")
            return redirect('/front')

        except:
            flash("プロフィールの変更に失敗しました...")
            return redirect('/front')

    else:
        return render_template('editprof.html')


@app.route('/front/studio')
@login_required  # ログイン済みかをチェックする
def tools():
    return render_template('studio.html')


@app.route('/front/login/signin', methods=['GET', 'POST'])
def signin():
    if request.method == "POST":
        try:
            useremail = request.form.get('useremail')
            password = request.form.get('password')

            # Userテーブルからusernameに一致するユーザを取得
            user = User.query.filter_by(useremail=useremail).first()
            if check_password_hash(user.password, password):
                login_user(user)

                flash("ログインしました！")
                return redirect('/front')

            else:
                flash("ログインに失敗しました...（原因と思われること：メールアドレスかパスワードを間違えている）")
                return redirect('/front/login/signin')

        except:
            flash("ログインに失敗しました...（原因と思われること：メールアドレスかパスワードを間違えている）")
            return redirect('/front/login/signin')

    else:
        return render_template('signin.html')


@app.route('/front/login/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        try:
            usericon = request.files['usericon']
            username = request.form.get('username')
            useremail = request.form.get('useremail')
            password = request.form.get('password')
            userdetail = " "

            iconUrl = username + ".jpg" # s3に保存するファイル名
            iconMetaData = "image/jpeg"  # フォーマットの指定 (画像)

            # S3 に アップロード （画像・動画 の保存は S3 に任せる）
            s3.upload_fileobj(usericon, Bucket, f'users/{iconUrl}', ExtraArgs={'ContentType': iconMetaData})

            # DBに入れるものを格納
            new_user = User(username=username, useremail=useremail, userdetail=userdetail, password=generate_password_hash(password, method='sha256'))  # パスワードをハッシュ値に変換
            db.session.add(new_user)  # DBに
            db.session.commit()  # コミット

            flash("アカウントの作成が完了しました。早速ログインしましょう！")
            return redirect('/front/login/signin')

        except:
            flash("アカウントの作成に失敗しました... (原因と思われること：既に同じユーザー名が存在する・入力漏れがある)")
            return redirect('/front/login/signup')

    else:
        return render_template('signup.html')


@app.route('/front/logout')
@login_required  # ログイン済みかをチェックする
def logout():
    logout_user()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
