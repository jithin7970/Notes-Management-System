from flask  import Flask,request,render_template,redirect,url_for,flash,session,send_file,jsonify
from flask_session import Session
from otp import genotp
from cemail import send_mail
from stoken import endata,dndata
from mysql.connector import (connection)
from io import BytesIO
import  re
import flask_excel as excel
mydb = connection.MySQLConnection(user='root',host='localhost',password="Admin@123",db='users')
app = Flask(__name__)
excel.init_excel(app)
app.secret_key = "supersecretkey"
app.config['SESSION_TYPE']='filesystem'
Session(app)
users = {}
@app.route('/')
def welcome():
    return render_template('index.html')

@app.route('/register',methods=['GET','POST'])
def register():
    error = None
    if request.method=='POST':
        username = request.form['username']
        usermail = request.form['email']
        password = request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s',[usermail])
            email_count=cursor.fetchone() #(1,) or (0,)
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not verify useremail')
            return redirect(url_for('register'))  
        else:
            if email_count[0]==0:
                otp = genotp()
                userdata = {'username':username,'useremail':usermail,'userpassword':password,'serverotp':otp}
                Subject = 'Your otp for snm application'
                Body = f'Use the given OTP for snp app : {otp}'
                send_mail(to=usermail,subject=Subject,body=Body)
                flash('otp has been sent to the mail')
                return redirect(url_for('verify',data_info=endata(userdata)))
            elif email_count[0]==1:
                flash('User already existed')
    return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        login_useremail = request.form['useremail']
        login_password = request.form['password']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s',[login_useremail])
            email_count = cursor.fetchone()[0]
            if email_count == 1:
                cursor.execute('select password from userdata where useremail = %s',[login_useremail])
                stored_password =cursor.fetchone()[0]
                if stored_password == login_password:
                    session['user']= login_useremail
                    return redirect(url_for('dashboard'))
                else:
                    flash('invalid password')
                    return redirect(url_for('login'))
            elif email_count == 0:
                flash('No email found pls register now')
                return redirect(url_for('register'))
            else:
                flash('invalid emailid')
                return redirect(url_for('userlogin'))
        except Exception as e:
            print(e)
            flash('couldnot verify login details')
            return redirect(url_for('userlogin'))
    return render_template('login.html')
@app.route('/verify/<data_info>',methods=['GET','POST'])
def verify(data_info):
    try:
        sdata = dndata(data_info)
    except Exception as e:
        print(e)
        flash('could not verify otp')
        return redirect(url_for('register'))
    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == sdata['serverotp']:
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('insert into userdata(username,useremail,password) values(%s,%s,%s)',
                               [sdata['username'],sdata['useremail'],sdata['userpassword']]) 
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('could not store the details')
        else:
            flash('Invalid OTP. Try again.')
    return render_template('verify.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if not session.get('user'):
        flash('please login to add a notes')
        return redirect(url_for('login'))
    if request.method=='POST':
        notes_title = request.form['title']
        notes_content = request.form['text']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
            user_id=cursor.fetchone()[0]
            cursor.execute('insert into notedata(notes_title,notes_content,user_id)  values(%s,%s,%s)',
                           [notes_title,notes_content,user_id])
            mydb.commit()
            cursor.close()
        except Exception as e:
            flash('could not store notesdetails')
            return redirect(url_for('addnotes'))
        else:
            flash('notes added successfully')
            return redirect(url_for('addnotes'))
    return render_template('addnotes.html')

@app.route('/viewallnotes')
def viewallnotes():
    if not session.get('user'):
        flash('please login to view all notes')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id = cursor.fetchone()[0]
        cursor.execute('select notesid,notes_title,created_at from notedata where user_id=%s',[user_id])
        notesdata=cursor.fetchall()
        print(notesdata)
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch notesdetails')
        return redirect(url_for('dashboard'))
    else:
        return render_template('viewallnotes.html',notesdata=notesdata)
    return render_template('viewallnotes.html')

@app.route('/viewnotes/<int:nid>')
def viewnotes(nid):
    if not session.get('user'):
        flash('please login to view notes')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(buffered=True)
        
        # Get current user id
        cursor.execute(
            'select userid from userdata where useremail=%s',
            [session.get('user')]
        )
        user_id = cursor.fetchone()[0]

        # Fetch only selected note
        cursor.execute(
            'select notesid, notes_title, notes_content, created_at from notedata where notesid=%s and user_id=%s',
            [nid, user_id]
        )

        notesdata = cursor.fetchone()
        cursor.close()

    except Exception as e:
        print(e)
        flash('could not fetch note details')
        return redirect(url_for('dashboard'))

    if not notesdata:
        flash('Note not found')
        return redirect(url_for('viewallnotes'))

    return render_template('viewnotes.html', notesdata=notesdata)

@app.route('/deletenotes/<int:nid>')
def deletenotes(nid):
    if not session.get('user'):
        flash('Please login to delete notes')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(buffered=True)

        # Get current user id
        cursor.execute(
            'select userid from userdata where useremail=%s',
            [session.get('user')]
        )
        user_id = cursor.fetchone()[0]

        # Delete only if note belongs to this user
        cursor.execute(
            'delete from notedata where notesid=%s and user_id=%s',
            [nid, user_id]
        )

        mydb.commit()
        cursor.close()

        if cursor.rowcount == 0:
            flash('Note not found or not authorized')
        else:
            flash('Note deleted successfully')

    except Exception as e:
        print(e)
        flash('Could not delete note')
        return redirect(url_for('viewallnotes'))

    return redirect(url_for('viewallnotes'))

@app.route('/updatenotes/<int:nid>', methods=['GET', 'POST'])
def updatenotes(nid):
    if not session.get('user'):
        flash('Please login to update notes')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            'select userid from userdata where useremail=%s',
            [session.get('user')]
        )
        user_id = cursor.fetchone()[0]

        if request.method == 'POST':
            updated_title = request.form['title']
            updated_content = request.form['text']

            cursor.execute(
                '''
                update notedata
                set notes_title=%s, notes_content=%s
                where notesid=%s and user_id=%s
                ''',
                [updated_title, updated_content, nid, user_id]
            )

            mydb.commit()

            if cursor.rowcount == 0:
                flash('Note not found or not authorized')
            else:
                flash('Note updated successfully')

            cursor.close()
            return redirect(url_for('viewallnotes'))

        cursor.execute(
            '''
            select notesid, notes_title, notes_content, created_at
            from notedata
            where notesid=%s and user_id=%s
            ''',
            [nid, user_id]
        )

        notesdata = cursor.fetchone()
        print(notesdata)
        cursor.close()

        if not notesdata:
            flash('Note not found')
            return redirect(url_for('viewallnotes'))

        return render_template('updatenotes.html', notesdata=notesdata)

    except Exception as e:
        print(e)
        flash('Could not update note')
        return redirect(url_for('viewallnotes'))
    
@app.route('/uploadfile',methods=['GET','POST'])
def uploadfile():
    if session.get('user'):
        if request.method=='POST':
            filedata=request.files['file']
            filename=filedata.filename
            f_data = filedata.read()
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                user_id = cursor.fetchone()[0]
                cursor.execute('insert into filedata(user_id,filename,filedata) values(%s,%s,%s)',[user_id,filename,f_data])
                mydb.commit()
                cursor.close()
                flash('file uploaded successfully')
                return redirect(url_for('uploadfile')) 
            except Exception as e:
                print(e)
                flash('could not uplaod file')
                return redirect(url_for('uploadfile'))
    else:
        flash('pls login to uplaod file')
        return redirect(url_for('login'))
    return render_template('uploadfile.html')

@app.route('/viewallfiles')
def viewallfiles():
    if not session.get('user'):
        flash('pls login to view all files')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()[0] #(1,)
        cursor.execute('select fid,filename,created_at from filedata where user_id=%s',[user_id]) #[(1,'anc','2026-02-23 2:56:2'),]
        allfilesdata=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch filesdetails')
        return redirect(url_for('dashboard'))
    else:
        return render_template('viewallfiles.html',filesdata=allfilesdata)


@app.route('/view_file/<fid>')
def view_file(fid):
    if not session.get('user'):
        flash('pls login to view all files')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id = cursor.fetchone()[0]
        cursor.execute('select fid,filename,filedata,created_at from filedata where user_id = %s and fid=%s',[user_id,fid])
        file_data = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(e)
        return redirect(url_for('viewallfiles'))
    else:
        bytesdata = BytesIO(file_data[2])
        return send_file(bytesdata,as_attachment=False,download_name=file_data[1])
    
@app.route('/download_file/<fid>')
def download_file(fid):
    if not session.get('user'):
        flash('pls login to view all files')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id = cursor.fetchone()[0]
        cursor.execute('select fid,filename,filedata,created_at from filedata where user_id = %s and fid=%s',[user_id,fid])
        file_data = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(e)
        return redirect(url_for('viewallfiles'))
    else:
        bytesdata = BytesIO(file_data[2])
        return send_file(bytesdata,as_attachment=True,download_name=file_data[1])
    

@app.route('/getexceldata')
def getexceldata():
    if not session.get('user'):
        flash('please login to view all notes')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id = cursor.fetchone()[0]
        cursor.execute('select notesid,notes_title,notes_content,created_at from notedata where user_id=%s',[user_id])
        notesdata=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)    
        flash('could not fetch notesdetails')
        return redirect(url_for('dashboard'))
    else:
        array_data = [list(i) for i in notesdata]
        columns = ['Notes Id','Notes Title','Notes Content','Created At']
        array_data.insert(0,columns)
        return excel.make_response_from_array(array_data,"xlsx",file_name="excelData")
    
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        flash('Logged out successfully')
        return redirect(url_for('login'))
    else:
        flash('You must login first')
        return redirect(url_for('login'))

@app.route('/delete_file/<fid>')
def delete_file(fid):
    if not session.get('user'):
        flash('please login first')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(buffered=True)

        cursor.execute(
            'select userid from userdata where useremail=%s',
            [session.get('user')]
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            'delete from filedata where fid=%s and user_id=%s',
            [fid, user_id]
        )

        mydb.commit()
        cursor.close()

        flash('file deleted successfully')

    except Exception as e:
        print(e)
        flash('could not delete file')

    return redirect(url_for('viewallfiles'))

@app.route('/search', methods=['POST'])
def search():

    if not session.get('user'):
        flash('please login first')
        return redirect(url_for('login'))

    search_data = request.form['sdata']

    try:
        cursor = mydb.cursor(buffered=True)

        cursor.execute(
            'select userid from userdata where useremail=%s',
            [session.get('user')]
        )

        user_id = cursor.fetchone()[0]

        cursor.execute(
            '''
            select notesid, notes_title, notes_content, created_at
            from notedata
            where user_id=%s
            and (notes_title like %s
                 or notes_content like %s
                 or created_at like %s)
            ''',
            [user_id,
             '%'+search_data+'%',
             '%'+search_data+'%',
             '%'+search_data+'%']
        )

        notesdata = cursor.fetchall()
        cursor.close()

        return render_template('viewallnotes.html', notesdata=notesdata)

    except Exception as e:
        print(e)
        flash('could not fetch notes')
        return redirect(url_for('dashboard'))

@app.route('/forgotpwd', methods=['GET','POST'])
def forgotpwd():

    if request.method == 'POST':

        useremail = request.form['email']

        try:
            cursor = mydb.cursor(buffered=True)

            cursor.execute(
                'select count(*) from userdata where useremail=%s',
                [useremail]
            )

            email_count = cursor.fetchone()[0]

            cursor.close()

        except Exception as e:
            print(e)
            flash('could not verify email')
            return redirect(url_for('forgotpwd'))

        else:

            if email_count == 1:

                subject = 'Reset Password Link'

                body = f"Click the link to reset password: {url_for('newpassword', data=endata(useremail), _external=True)}"

                send_mail(to=useremail, subject=subject, body=body)

                flash('reset link sent to your email')

                return redirect(url_for('login'))

            else:

                flash('Email not found')

    return render_template('forgotpwd.html')

@app.route('/newpassword/<data>', methods=['GET','PUT'])
def newpassword(data):

    if request.method == 'PUT':

        npassword = request.get_json()['password']

        try:
            useremail = dndata(data)

            cursor = mydb.cursor(buffered=True)

            cursor.execute(
                'update userdata set password=%s where useremail=%s',
                [npassword, useremail]
            )

            mydb.commit()
            cursor.close()

            return jsonify({"message":"password updated"})

        except Exception as e:
            print(e)
            return jsonify({"message":"failed"})

    return render_template('newpassword.html',data=data)

if __name__=='__main__':
    app.run(debug=True,use_reloader=True)