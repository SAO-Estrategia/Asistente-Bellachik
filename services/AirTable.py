import requests

class AirtablePATManager:
    def __init__(self, base_id, table_name, access_token):
        """
        Inicializa el cliente de Airtable con un token de acceso personal.

        Args:
            base_id (str): ID de la base de Airtable.
            table_name (str): Nombre de la tabla dentro de la base.
            access_token (str): Token de acceso personal para autenticar las solicitudes.
        """
        self.base_url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        self.base_id = base_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def list_records(self, max_records=10, view=None):
        """
        Lista los registros de la tabla.

        Args:
            max_records (int): Número máximo de registros a recuperar.
            view (str, optional): Vista específica desde la cual recuperar registros.

        Returns:
            dict: Respuesta de la API de Airtable con los registros.
        """
        params = {"maxRecords": max_records}
        if view:
            params["view"] = view

        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al listar registros: {e}")
            return None

    def create_record(self, dataRequest):
        """
        Crea un nuevo registro en la tabla.

        Args:
            fields (dict): Campos y valores para el nuevo registro.

        Returns:
            dict: Respuesta de la API de Airtable para el registro creado.
        """
        data = dataRequest
        try:
            response = requests.post(self.base_url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al crear un registro: {e}")
            return None
        

    def update_record(self, record_id, fields):
        """
        Actualiza un registro existente en la tabla.

        Args:
            record_id (str): ID del registro a actualizar.
            fields (dict): Campos y valores a actualizar.

        Returns:
            dict: Respuesta de la API de Airtable para el registro actualizado.
        """
        url = f"{self.base_url}/{record_id}"
        data = {"fields": fields}
        try:
            response = requests.patch(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al actualizar el registro: {e}")
            return None

    def delete_record(self, record_id):
        """
        Elimina un registro de la tabla.

        Args:
            record_id (str): ID del registro a eliminar.

        Returns:
            dict: Respuesta de la API de Airtable para el registro eliminado.
        """
        url = f"{self.base_url}/{record_id}"
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al eliminar el registro: {e}")
            return None
        
    def guardar_usuario_servicio(self,nombre, telefono, correo, servicio_agendado):
        """
        Guarda la información del usuario y el servicio agendado en una tabla de Airtable.

        Args:
            nombre (str): Nombre del usuario.
            telefono (str): Número de teléfono del usuario.
            correo (str): Correo electrónico del usuario.
            servicio_agendado (str): Descripción del servicio agendado.

        Returns:
            dict: Resultado estandarizado indicando éxito o error.
        """
        try:
            # Construir el cuerpo de la solicitud
            user_data = {
                "fields": {
                    "Nombre": nombre,
                    "Teléfono": telefono,
                    "Correo": correo,
                    "Servicio Agendado": servicio_agendado
                }
            }

            # Llamar a la función para crear el registro
            response = self.create_record(user_data)

            # Verificar la respuesta
            if response and 'id' in response:
                return {
                    "message": "El usuario se ha guardado exitosamente.",
                    "data": {
                        "id": response['id'],
                        "nombre": nombre,
                        "telefono": telefono,
                        "correo": correo,
                        "servicio_agendado": servicio_agendado
                    }
                }
            else:
                return {
                    "message": "No se pudo guardar el usuario en la tabla de Airtable.",
                    "error": response
                }

        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return {
                "message": "Ocurrió un error al guardar el usuario.",
                "error": str(e)
            }

    def update_user_info(self, telefono, nombre=None, email=None, servicio_agendado=None):
        """
        Actualiza un registro en Airtable basado en el teléfono proporcionado.

        Args:
            telefono (str): Número de teléfono para identificar el registro.
            nombre (str, optional): Nuevo nombre del usuario.
            email (str, optional): Nuevo correo electrónico.
            servicio_agendado (str, optional): Nuevo servicio agendado.

        Returns:
            dict: Resultado de la operación.
        """
        try:
            # Obtener registros existentes que coincidan con el teléfono
            records = self.list_records(max_records=100)
            record_to_update = None

            for record in records.get("records", []):
                if record["fields"].get("Teléfono") == telefono:
                    record_to_update = record
                    break

            if not record_to_update:
                return {"message": "No se encontró ningún registro con el teléfono proporcionado."}

            # Construir los campos a actualizar
            updated_fields = {}
            if nombre:
                updated_fields["Nombre"] = nombre
            if email:
                updated_fields["Correo"] = email
            if servicio_agendado:
                updated_fields["Servicio Agendado"] = servicio_agendado

            if not updated_fields:
                return {"message": "No se proporcionaron campos para actualizar."}

            # Actualizar el registro
            record_id = record_to_update["id"]
            response = self.update_record(record_id, updated_fields)

            return {
                "message": "El registro se actualizó exitosamente.",
                "data": response
            }

        except Exception as e:
            return {"message": "Error al actualizar el registro.", "error": str(e)}
    
    def leer_registros(self, nombre=None, email=None, telefono=None):
        """
        Lee registros de Airtable filtrando por nombre, email o teléfono.

        Args:
            nombre (str, optional): Nombre del usuario.
            email (str, optional): Correo electrónico del usuario.
            telefono (str, optional): Teléfono del usuario.

        Returns:
            dict: Lista de registros encontrados.
        """
        try:
            # Obtener todos los registros
            records = self.list_records(max_records=100)
            filtered_records = []

            for record in records.get("records", []):
                fields = record.get("fields", {})
                match = True

                if nombre and nombre.lower() not in fields.get("Nombre", "").lower():
                    match = False
                if email and email.lower() != fields.get("Correo", "").lower():
                    match = False
                if telefono and telefono != fields.get("Teléfono", ""):
                    match = False

                if match:
                    filtered_records.append({
                        "id": record.get("id"),
                        "Nombre": fields.get("Nombre"),
                        "Correo": fields.get("Correo"),
                        "Teléfono": fields.get("Teléfono"),
                        "Servicio Agendado": fields.get("Servicio Agendado", "")
                    })

            if not filtered_records:
                return {"message": "No se encontraron registros que coincidan con los criterios de búsqueda."}

            return {"message": "Registros encontrados.", "data": filtered_records}

        except Exception as e:
            return {"message": "Error al leer los registros.", "error": str(e)}
        
    def borrar_registro(self, telefono=None, email=None):
        """
        Elimina un registro de Airtable basado en el teléfono o correo electrónico.

        Args:
            telefono (str, optional): Teléfono del usuario para identificar el registro.
            email (str, optional): Correo electrónico del usuario para identificar el registro.

        Returns:
            dict: Resultado de la operación.
        """
        try:
            if not telefono and not email:
                return {"message": "Debe proporcionar un teléfono o un correo electrónico para borrar un registro."}

            # Obtener registros existentes
            records = self.list_records(max_records=100)
            record_to_delete = None

            for record in records.get("records", []):
                fields = record.get("fields", {})
                if telefono and fields.get("Teléfono") == telefono:
                    record_to_delete = record
                    break
                if email and fields.get("Correo") == email:
                    record_to_delete = record
                    break

            if not record_to_delete:
                return {"message": "No se encontró ningún registro con los criterios proporcionados."}

            # Eliminar el registro
            record_id = record_to_delete["id"]
            response = self.delete_record(record_id)

            return {
                "message": "El registro se eliminó exitosamente.",
                "data": response
            }

        except Exception as e:
            return {"message": "Error al borrar el registro.", "error": str(e)}

    def crear_registro_generico(nombre_tabla, campos):
        """
        Crea un registro en Airtable de manera genérica con nombre de tabla y campos variables.

        Args:
            nombre_tabla (str): El nombre de la tabla donde se insertará el registro.
            campos (dict): Diccionario con los nombres de los campos y sus valores.

        Returns:
            dict: Resultado de la operación indicando éxito o error.
        """
        try:
            # Configurar la instancia del manejador con la tabla específica
            airtable_manager = AirtablePATManager(
                base_id="appPxbcEhfogVOxis",  # Reemplaza con tu Base ID
                table_name=nombre_tabla,      # Nombre dinámico de la tabla
                access_token="pathw9Bc7ngfzbTKD.388179deaf58e44731e0dc88782fc801517d26b589322e9122949c06720f1625"  # Token de acceso personal
            )

            # Validar que el diccionario de campos no esté vacío
            if not campos or not isinstance(campos, dict):
                return {"message": "Los campos proporcionados no son válidos o están vacíos."}

            # Crear el cuerpo de la solicitud
            data_request = {"fields": campos}

            # Llamar al método create_record de la clase AirtablePATManager
            response = airtable_manager.create_record(data_request)

            # Verificar y formatear la respuesta
            if response and 'id' in response:
                return {
                    "message": "El registro se ha creado exitosamente.",
                    "data": {
                        "id": response['id'],
                        "fields": campos
                    }
                }
            else:
                return {
                    "message": "No se pudo crear el registro en la tabla de Airtable.",
                    "error": response
                }

        except Exception as e:
            print(f"Error inesperado al crear el registro: {str(e)}")
            return {
                "message": "Ocurrió un error inesperado al crear el registro.",
                "error": str(e)
            }
