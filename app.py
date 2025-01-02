from flask import Flask, request, jsonify
import requests
#import functions
import openai
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build

from services.GoogleCalendar import GoogleCalendarManager
from services.AirTable import AirtablePATManager
from services.Gmail import GmailManager
from services.GoogleDocs import GoogleDocsManager

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

#creds = functions.authenticate_google()

user_threads = {}

@app.route("/")
def home():
    return "Asistente Bellachik está en línea"

@app.route('/asistente_bellachik', methods=['POST'])
def asistente_bellachik():   
    try:
        # Obtener datos de la solicitud
        data = request.get_json()
        if data is None or 'message' not in data or 'thread_id' not in data:
            return jsonify({'status': 'error', 'message': 'Se requieren los campos "message" y "thread_id" en el JSON.'}), 400

        user_message = data['message']
        thread_id = data['thread_id']
        customer = data['customer']  # Información del cliente enviada en el request
        print(f"Mensaje del usuario ({thread_id}): {user_message}")
        
        #En caso de no tener thread_id, se crea un nuevo hilo
        if not thread_id:
            thread = openai.beta.threads.create()
            thread_id = thread.id
            print(f"Nuevo thread_id creado: {thread_id}")
        
        # Agregar el mensaje del usuario al hilo
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
        )

        # Ejecutar el asistente
        assistant_id = os.getenv("ASSISTANT_ID")
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        # Manejar estado del run
        while run.status not in ("completed", "failed", "requires_action"):
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id,
            )
            
        if run.status == "requires_action":
            
            tools_to_call = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs_array = []  # Array para almacenar las respuestas de las herramientas
            
            # Instanciar el gestor de Google Calendar
            calendar_manager = GoogleCalendarManager()
            
             # Configuración de Airtable        
            base_id = os.getenv("BASE_ID")
            access_token = os.getenv("ACCESS_TOKEN")

            # Crear instancia del manejador de Airtable
            airtable_manager = AirtablePATManager(base_id, access_token)
            
            
            
            # Diccionario de mapeo de funciones
            function_map = {
                #Funciones para GoogleCalendar
                
                # Funciones para AirTable
                "consultar_cliente": lambda intencion_cliente: format_customer_information(customer),
                #"actualizar_cliente": lambda id_cliente, campos_actualizar: airtable_manager.actualizar_cliente(id_cliente=id_cliente,campos_actualizar=campos_actualizar),
                "actualizar_cliente": lambda customer: airtable_manager.actualizar_cliente(
                    id_cliente=customer.get("id_cliente"),
                    campos_actualizar={
                        key: value for key, value in customer.items()
                        if key not in ["id_cliente", "hilo_conversacion"] and value
                    }
                ),
                
                # "detect_human_interaction_intent": lambda **kwargs: {
                #     "Estado": "Programada",
                #     "Cliente relacionado": (
                #         buscar_usuario(kwargs.get("nombre_cliente")) or solicitar_datos_usuario(thread_id)
                #     ),
                #     "Tipo": "Alerta",
                #     "Asunto": "Solicitud de asesor",
                #     "Descripción": kwargs.get("user_message", "Descripción no proporcionada"),
                #     "Medio de Envío": "WhatsApp"
                # },
                
            }
            
            for tool_call in tools_to_call:
                print(tool_call)
                tool_name = tool_call.function.name
                tool_arguments = json.loads(tool_call.function.arguments)  # Parsear argumentos de la herramienta
                
                print(f"Procesando herramienta: {tool_name}")
                print(f"Argumentos: {tool_arguments}")
                
                if tool_name in function_map:
                    # Llamar a la función mapeada dinámicamente
                    function = function_map[tool_name]
                    try:
                        # Ejecutar la función con los argumentos descompuestos
                        result = function(**tool_arguments)
                        print("RESULT DEL LLAMDA A LA FUNCION")
                        print(result)
                        tool_outputs_array.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result) 
                        })
                        #"output": json.dumps(result if result else {"success": True})
                    except Exception as e:
                        print(f"Error al ejecutar {tool_name}: {str(e)}")
                        tool_outputs_array.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"error": str(e)})
                        })
                
                else:
                    print(f"Herramienta desconocida: {tool_name}")
                    tool_outputs_array.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps({"error": f"Tool {tool_name} not implemented"})
                    })
                # Responder al asistente con la salida
                run = openai.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs_array
                )                

        # Obtener mensajes del hilo
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        assistant_messages = [
            msg.content[0].text.value
            for msg in messages if msg.role == "assistant"
        ]
        #last_assistant_message = assistant_messages[-1] if assistant_messages else "No hay mensajes del asistente."
        
        responses = [
            {"role": msg.role, "content": msg.content[0].text.value, "thread_id": thread_id}
            for msg in messages
            #Regresar el thread_id
        ]
        #print(responses)

        return jsonify({'status': 'success', 'messages': responses}), 200
        #return jsonify({'status': 'success', 'message': last_assistant_message, "thread_id": thread_id}), 200

    except Exception as e:
        print(f'Error inesperado: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Error inesperado: {str(e)}'}), 500


def format_customer_information(customer):
    """
    Formatea la información del cliente en una cadena legible.

    Args:
        customer (dict): Objeto que contiene los datos del cliente.

    Returns:
        dict: Diccionario con el mensaje formateado.
    """
    try:
        print("Llamando a la funcion")
        print(customer)
        # Verificar si hay información suficiente
        if not customer or all(not customer.get(key) for key in ['nombre_completo', 'telefono_movil', 'correo_electronico']):
            print("dentro del if")
            return {
                "status": "error",
                "message": "No se encontraron datos suficientes del cliente para mostrar."
            }

        # Preparar los datos disponibles del cliente
        datos_cliente = []
        if customer.get('nombre_completo'):
            datos_cliente.append(f"- Nombre: {customer['nombre_completo']}")
        if customer.get('telefono_movil'):
            datos_cliente.append(f"- Teléfono: {customer['telefono_movil']}")
        if customer.get('correo_electronico'):
            datos_cliente.append(f"- Correo: {customer['correo_electronico']}")
        if customer.get('domicilio'):
            datos_cliente.append(f"- Domicilio: {customer['domicilio']}")
        if customer.get('fecha_nacimiento'):
            datos_cliente.append(f"- Fecha de Nacimiento: {customer['fecha_nacimiento']}")
        if customer.get('edad'):
            datos_cliente.append(f"- Edad: {customer['edad']}")
        if customer.get('sexo'):
            datos_cliente.append(f"- Sexo: {customer['sexo']}")

        # Generar el mensaje formateado
        mensaje = "Estos son tus datos registrados:\n" + "\n".join(datos_cliente)
        
        print(mensaje);

        return {
            "status": "success",
            "message": mensaje
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Ocurrió un error al formatear la información del cliente: {str(e)}"
        }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    #app.run()