from flask import Flask, redirect
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField
from wtforms.validators import DataRequired
from flask_socketio import SocketIO
import datetime

app = Flask(__name__)
db = SQLAlchemy(app)
app.config.from_pyfile('config.py')
socketio = SocketIO(app, async_mode=None)


@app.template_filter('datetime')
def format_datetime(value):
    if value:
        return value.strftime(format='%d.%m.%y %H:%M:%S')
    else:
        return '<Дата отсутствует>'


def reload_clients():
    socketio.emit('reload', namespace='')


class MealForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    price = DecimalField('Цена', validators=[DataRequired()])


class OrderForm(FlaskForm):
    meal_id = SelectField('Блюдо', coerce=int)


@app.route("/")
@app.route("/hall")
def hall():
    buttons = [
        {
            'title': 'Отменить',
            'action': 3,
            'referrer': 'hall'
        }
    ]
    orders = Order.query.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('order_index.html', orders=orders, buttons=buttons, title='Зал')


@app.route("/kitchen")
def kitchen():
    buttons = [
        {
            'title': 'В работе',
            'action': 1,
            'referrer': 'kitchen'
        },
        {
            'title': 'Готов',
            'action': 2,
            'referrer': 'kitchen'
        }
    ]
    orders = Order.query.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('order_index.html', orders=orders, buttons=buttons, title='Кухня')


@app.route("/meal")
def meal_index():
    meals = Meal.query.all()
    return render_template("meal_index.html", meals=meals, title='Список блюд')


@app.route("/meal/create", methods=('GET', 'POST'))
def create_meal():
    form = MealForm()
    if form.validate_on_submit():
        db.session.add(Meal(form.name.data, form.price.data))
        db.session.commit()
        return redirect('meal')
    return render_template("meal_create.html", form=form, title='Добавление блюда')


# @app.route("/meal/delete/<id>")
# def meal_delete(id):
#     meal_order = Order.query.filter_by(meal_id=id).first()
#     if meal_order:
#         return redirect('meal')
#     meal = Meal.query.get(id)
#     db.session.delete(meal)
#     db.session.commit()
#     return redirect('meal')


@app.route("/order/create", methods=('GET', 'POST'))
def order_create():
    form = OrderForm()
    if form.is_submitted():
        meal_id = form.meal_id.data
        meal = Meal.query.get(meal_id)
        order = Order(meal)
        order.price = meal.price
        db.session.add(order)
        db.session.commit()
        reload_clients()
        return redirect('hall')
    form.meal_id.choices = [(m.id, m.name) for m in Meal.query.all()]
    return render_template('order_create.html', form=form, title='Сделать заказ')


@app.route("/order/set_state/<orderid>/<state>/<referrer>")
def order_in_work(orderid, state, referrer):
    order = Order.query.get(orderid)
    order.state = state
    if state == '1':
        order.cooking_at = datetime.datetime.now()
    if state == '2':
        order.ready_at = datetime.datetime.now()
    db.session.commit()
    reload_clients()
    if referrer in ['hall', 'kitchen']:
        return redirect(referrer)


class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    price = db.Column(db.Float)

    def __init__(self, name, price):
        self.name = name
        self.price = price

    def __repr__(self):
        return '<Meal %r>' % self.name


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))
    meal = db.relationship('Meal', backref=db.backref('meals', lazy='dynamic'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    state = db.Column(db.Integer, default=0)
    cooking_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Float)

    def __init__(self, meal):
        self.meal = meal


if __name__ == '__main__':
    socketio.run(app)
