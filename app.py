import os
import random
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

# ---------- Config ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "troque_essa_chave_para_producao"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SQLite (arquivo cupcakes.db no diretório do projeto)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cupcakes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<User {self.nome} | {self.email}>"

class Cupcake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sabor = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.String(500), nullable=True)
    detalhes = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    imagem = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f"<Cupcake {self.sabor} | R${self.preco}>"

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_numero = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    itens = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    cupcake_id = db.Column(db.Integer, db.ForeignKey('cupcake.id'))
    quantidade = db.Column(db.Integer, default=1)
    preco_unit = db.Column(db.Float, nullable=False)

    cupcake = db.relationship('Cupcake')


# ---------- Inicialização do DB ----------
def init_db():
    db.create_all()
    print("Banco de dados inicializado com sucesso!")
    print("Pasta de uploads verificada.")

    if not User.query.filter_by(email='admin@cupcake.com').first():
        admin = User(
            nome='Admin',
            email='admin@cupcake.com',
            senha_hash=generate_password_hash('123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado.")

    if Cupcake.query.count() == 0:
        default1 = Cupcake(sabor='Morango com Ninho', descricao='Massa macia com Ninho', detalhes='Delicioso', preco=6.50)
        default2 = Cupcake(sabor='Chocolate Belga', descricao='Cobertura de chocolate belga', detalhes='Intenso', preco=7.00)
        default3 = Cupcake(sabor='Ninho', descricao='Massa fofinha com recheio de Ninho', detalhes='Perfeito para festas', preco=6.00)
        default4 = Cupcake(sabor='Red Velvet', descricao='Bolo vermelho com cream cheese', detalhes='Clássico americano', preco=7.50)
        default5 = Cupcake(sabor='Bicho de Pé', descricao='Massa rosa com cobertura de leite condensado', detalhes='Delícia nostálgica', preco=6.80)
        db.session.add_all([default1, default2, default3, default4, default5])
        db.session.commit()
        print("Cupcakes iniciais criados.")

# ---------- Auth ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        if not nome or not email or not senha:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('register'))

        if '@' not in email or '.' not in email:
            flash('Email inválido.', 'error')
            return redirect(url_for('register'))

        if len(senha) < 6:
            flash('Senha deve ter pelo menos 6 caracteres.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado. Faça login.', 'error')
            return redirect(url_for('login'))

        novo = User(nome=nome, email=email, senha_hash=generate_password_hash(senha), is_admin=False)
        db.session.add(novo)
        db.session.commit()

        session['user_id'] = novo.id
        session['nome'] = novo.nome
        session['is_admin'] = novo.is_admin
        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for('venda'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        if not email or not senha:
            flash('Preencha todos os campos.', 'error')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(senha):
            session['user_id'] = user.id
            session['nome'] = user.nome
            session['is_admin'] = user.is_admin

            flash(f'Bem-vindo, {user.nome}!', 'success')

            if user.is_admin:
                return redirect(url_for('admin_list'))
            return redirect(url_for('venda'))

        flash('Email ou senha inválidos.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- Admin ----------
@app.route('/admin/cupcakes')
def admin_list():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    cupcakes = Cupcake.query.order_by(Cupcake.id.desc()).all()
    return render_template('admin_list.html', cupcakes=cupcakes)

@app.route('/admin/cupcakes/new', methods=['GET', 'POST'])
def admin_new():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        sabor = request.form['sabor']
        descricao = request.form.get('descricao')
        detalhes = request.form.get('detalhes')
        preco = float(request.form['preco'])
        imagem = request.files.get('imagem')
        filename = None
        if imagem and imagem.filename != '':
            filename = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_c = Cupcake(sabor=sabor, descricao=descricao, detalhes=detalhes, preco=preco, imagem=filename)
        db.session.add(new_c)
        db.session.commit()
        return redirect(url_for('admin_list'))
    return render_template('admin_form.html', cupcake=None)

@app.route('/admin/cupcakes/<int:id>/edit', methods=['GET', 'POST'])
def admin_edit(id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    cupcake = Cupcake.query.get_or_404(id)
    if request.method == 'POST':
        cupcake.sabor = request.form['sabor']
        cupcake.descricao = request.form.get('descricao')
        cupcake.detalhes = request.form.get('detalhes')
        cupcake.preco = float(request.form['preco'])
        imagem = request.files.get('imagem')
        if imagem and imagem.filename != '':
            filename = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cupcake.imagem = filename
        db.session.commit()
        return redirect(url_for('admin_list'))
    return render_template('admin_form.html', cupcake=cupcake)

@app.route('/admin/cupcakes/<int:id>/delete', methods=['POST'])
def admin_delete(id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    cupcake = Cupcake.query.get_or_404(id)
    if cupcake.imagem:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], cupcake.imagem))
        except Exception:
            pass
    db.session.delete(cupcake)
    db.session.commit()
    return redirect(url_for('admin_list'))

# ---------- Vitrine ----------
@app.route('/venda')
def venda():
    nome = session.get('nome', 'Visitante')

    # Recebe parâmetros GET
    busca = request.args.get('busca', '').strip()
    ordenar = request.args.get('ordenar', '')

    # Query inicial
    query = Cupcake.query

    # Filtra pelo sabor
    if busca:
        query = query.filter(Cupcake.sabor.ilike(f"%{busca}%"))

    # Ordena pelo preço
    if ordenar == 'menor':
        query = query.order_by(Cupcake.preco.asc())
    elif ordenar == 'maior':
        query = query.order_by(Cupcake.preco.desc())
    else:
        query = query.order_by(Cupcake.id.desc())  # ordem padrão

    cupcakes = query.all()
    return render_template('venda.html', cupcakes=cupcakes, nome=nome)

# ---------- Carrinho ----------
@app.route('/cart/add/<int:cupcake_id>')
def cart_add(cupcake_id):
    c = Cupcake.query.get_or_404(cupcake_id)
    sacola = session.get('sacola', [])

    # Se o cupcake já está na sacola, aumenta a quantidade
    for item in sacola:
        if item['id'] == c.id:
            item['quantidade'] += 1
            break
    else:
        sacola.append({'id': c.id, 'sabor': c.sabor, 'preco': c.preco, 'quantidade': 1})

    session['sacola'] = sacola
    session.modified = True
    return redirect(url_for('venda'))


@app.route('/cart/remove/<int:cupcake_id>')
def cart_remove(cupcake_id):
    sacola = session.get('sacola', [])
    # Remove apenas o item com o id correspondente
    nova_sacola = [item for item in sacola if item['id'] != cupcake_id]
    session['sacola'] = nova_sacola
    session.modified = True
    return redirect(url_for('sacola'))


@app.route('/sacola/atualizar', methods=['POST'])
def atualizar_sacola():
    sacola = session.get('sacola', [])
    for item in sacola:
        nova_qtd = request.form.get(f"quantidade_{item['id']}")
        if nova_qtd and nova_qtd.isdigit():
            item['quantidade'] = int(nova_qtd)
    session['sacola'] = sacola
    session.modified = True
    return redirect(url_for('sacola'))


@app.route('/sacola')
def sacola():
    sacola = session.get('sacola', [])
    # Soma total considerando quantidade
    total = sum(item['preco'] * item['quantidade'] for item in sacola)
    nome = session.get('nome', 'Visitante')
    return render_template('sacola.html', sacola=sacola, total=total, nome=nome)


@app.route('/finalizar')
def finalizar():
    sacola = session.get('sacola', [])
    if not sacola:
        return redirect(url_for('venda'))

    total = sum(item['preco'] * item['quantidade'] for item in sacola)
    user_id = session.get('user_id')
    pedido_numero = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S') + str(random.randint(100, 999))
    order = Order(pedido_numero=pedido_numero, user_id=user_id, total=total)
    db.session.add(order)
    db.session.commit()

    for it in sacola:
        oi = OrderItem(order_id=order.id, cupcake_id=it['id'],
                       quantidade=it['quantidade'], preco_unit=it['preco'])
        db.session.add(oi)

    db.session.commit()
    session.pop('sacola', None)
    return render_template('confirmacao.html', pedido_numero=pedido_numero)


@app.route('/meus_pedidos')
def meus_pedidos():
    user_id = session.get('user_id')
    if not user_id:
        flash('Você precisa estar logado para ver seus pedidos.', 'error')
        return redirect(url_for('login'))

    pedidos = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template('meus_pedidos.html', pedidos=pedidos)


@app.route('/cupcake/<int:id>')
def cupcake_details(id):
    c = Cupcake.query.get_or_404(id)
    nome = session.get('nome', 'Visitante')
    return render_template('detalhes.html', cupcake=c, nome=nome)


# ---------- Uploads ----------
@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------- Página Inicial ----------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/api/cupcakes')
def api_cupcakes():
    busca = request.args.get('busca', '').strip()
    ordenar = request.args.get('ordenar', '')
    query = Cupcake.query

    if busca:
        query = query.filter(Cupcake.sabor.ilike(f"%{busca}%"))

    if ordenar == 'menor':
        query = query.order_by(Cupcake.preco.asc())
    elif ordenar == 'maior':
        query = query.order_by(Cupcake.preco.desc())
    else:
        query = query.order_by(Cupcake.id.desc())

    cupcakes = query.all()

    # Retorna JSON
    resultado = []
    for c in cupcakes:
        imagem_url = url_for('uploads', filename=c.imagem) if c.imagem else url_for('static', filename='uploads/default.png')
        resultado.append({
            'id': c.id,
            'sabor': c.sabor,
            'descricao': c.descricao,
            'preco': "%.2f" % c.preco,
            'imagem': imagem_url
        })
    return resultado

# ---------- Execução ----------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
