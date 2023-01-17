class Error401(Exception):

    def __str__(self):

        return "Error en credenciales: Revise el usuario y el password"

class Error405(Exception):

    def __str__(self):

        return "Error en metodo: el metodo de la peticion"

class ConnectionError(Exception):

    def __str__(self):

        return "Error en establecer la conexion: Revise la url"

class CompanyGPIntegrationError(Exception):

    def __str__(self):

        return "Error: compania no tiene configurado el Gp Phonix Integration Enviroment"
        