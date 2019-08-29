from flask import Flask, Blueprint
from resistanceEndpoints import ns as resistanceNamespace
from helper import api, logger, configureApp, configureLogging

def initializeApp(flask_app):
    configureLogging()
    configureApp(flask_app)
    blueprint = Blueprint('api', __name__, url_prefix='/api/v1')
    api.init_app(blueprint)
    api.add_namespace(resistanceNamespace)
    flask_app.register_blueprint(blueprint)
        
def create_app():
    app = Flask(__name__) 
    initializeApp(app)
    logger.info('>>>>> Starting server <<<<<')
    return app    

#To run with gunicorn
app = create_app()

#To run in development env
if __name__ == "__main__":
    logger.info('>>>>> Runnning at http://{0}:{1}/api/v1 <<<<<'.format(app.config['SERVER_IP'],app.config['SERVER_PORT']))
    app.run(host=app.config['SERVER_IP'],port=app.config['SERVER_PORT'],debug=app.config['FLASK_DEBUG'])