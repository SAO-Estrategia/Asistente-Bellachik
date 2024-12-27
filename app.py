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
from dotenv import load_dotenv

from services.GoogleCalendar import GoogleCalendarManager
from services.AirTable import AirtablePATManager
from services.Gmail import GmailManager
from services.GoogleDocs import GoogleDocsManager
from services.WhatsApp import WhatsApp_Manager

app = Flask(__name__)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
WHATSAPP_BUSINESS_ID = '439452585928337'
BASE_URL = f"https://graph.facebook.com/v16.0/{WHATSAPP_BUSINESS_ID}/messages"


SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

#creds = functions.authenticate_google()

user_threads = {}

@app.route("/")
def home():
    return "Asistente Bellachik está en línea"

app = Flask(__name__)



@app.route('/send_whatsapp_message', methods=['POST'])
def send_whatsapp_message():
    """
    Endpoint para enviar un mensaje usando WhatsAppManager.
    Espera un JSON con la estructura:
    {
      "phone_number": "<whatsapp_phone_number>",  # Ejemplo: "5491112345678"
      "message": "Mensaje de prueba"
    }
    """
    whatsapp_manager = WhatsApp_Manager(ACCESS_TOKEN, PHONE_NUMBER_ID)

    body = request.get_json()
    if not body:
        return jsonify({"error": "Missing JSON body"}), 400

    phone_number = body.get('phone_number')
    message = body.get('message')

    if not phone_number or not message:
        return jsonify({"error": "Missing phone_number or message"}), 400

    # Usamos la clase WhatsAppManager para enviar el mensaje
    response = whatsapp_manager.send_message(phone_number, message)

    if response.status_code == 200:
        return jsonify({
            "status": "success",
            "data": response.json()
        }), 200
    else:
        return jsonify({
            "status": "error",
            "code": response.status_code,
            "data": response.json()
        }), response.status_code


@app.route('/asistente_bellachik', methods=['POST'])
def asistente_bellachik():   
    try:
        # Obtener datos de la solicitud
        data = request.get_json()
        if data is None or 'message' not in data or 'thread_id' not in data:
            return jsonify({'status': 'error', 'message': 'Se requieren los campos "message" y "thread_id" en el JSON.'}), 400

        user_message = data['message']
        thread_id = data['thread_id']
        print(f"Mensaje del usuario ({thread_id}): {user_message}")
        
        #En caso de no tener thread_id, se crea un nuevo hilo
        if thread_id == "":
            thread = openai.beta.threads.create()
            thread_id = thread.id
            print(thread.id)
        
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
            table_name = "Usuarios"
            access_token = os.getenv("ACCESS_TOKEN")

            # # Crear instancia del manejador de Airtable
            airtable_manager = AirtablePATManager(base_id, table_name, access_token)

            # Diccionario de mapeo de funciones
            function_map = {
                #Funciones para GoogleCalendar
                "create_google_calendar_event": calendar_manager.create_google_calendar_event,
                "delete_google_calendar_event": calendar_manager.delete_google_calendar_event_by_details,
                "get_google_calendar_events": calendar_manager.get_google_calendar_events,
                "update_event_calendar": calendar_manager.update_event,
                "get_appointments": calendar_manager.get_appointments,   
                "cancel_appointment": calendar_manager.cancel_appointment,
                
                # Funciones para AirTable
                
                "create_airtable_record": airtable_manager.create_airtable_record,
                # "update_user_info": airtable_manager.update_user_info,
                # "leer_registros": airtable_manager.leer_registros,
                # "borrar_registro": airtable_manager.borrar_registro
                
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
                
                run = openai.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs_array
                )                

        # Obtener mensajes del hilo
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        responses = [
            {"role": msg.role, "content": msg.content[0].text.value, "thread_id": thread_id}
            for msg in messages
            #Regresar el thread_id
        ]
        #print(responses)

        return jsonify({'status': 'success', 'messages': responses}), 200

    except Exception as e:
        print(f'Error inesperado: {str(e)}')
        return jsonify({'status': 'error', 'message': f'Error inesperado: {str(e)}'}), 500

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000)
    app.run()