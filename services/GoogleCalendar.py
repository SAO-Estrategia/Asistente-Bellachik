import os.path
import datetime as dt
import json
import pickle

from datetime import datetime, timezone, timedelta
import sys
from googleapiclient.discovery import build

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES =[ "https://www.googleapis.com/auth/calendar", 'https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendarManager:
    def __init__(self):
        self.service = self._authenticate()
        
    def _authenticate(self):
        """
        Maneja la autenticación con Google Calendar mediante Service Account.
        """
        # Leer las credenciales de la variable de entorno
        credentials_json = os.getenv("CALENDAR_CREDENTIALS")
        if not credentials_json:
            raise EnvironmentError("La variable de entorno 'CALENDAR_CREDENTIALS' no está configurada.")
        
        # Cargar las credenciales desde el JSON en la variable de entorno
        credentials_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

        # Crear y devolver el servicio de Google Calendar
        return build("calendar", "v3", credentials=creds)
            
    def list_upcoming_events(self, max_results=10):
        now = dt.datetime.now().isoformat() + "Z"
        tomorrow = (dt.datetime.now() + dt.timedelta(days=5)).replace(hour=23, minute=59, second=0, microsecond=0).isoformat() + "Z"
        
        events_result = self.service.events().list(
            calendarId='primary', timeMin=now, timeMax=tomorrow,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                #print("EL EVENTO")
                #print( event )
                #print("El evento encontrado comienza a las ",start, event['summary'],event['id'])
                print("El evento ", event['summary'], " comienza a las ", start, " y termina a las ", end, " el identificador es: ", event['id'])
        
        return events
    
    def get_google_calendar_events(creds, time_min, time_max):

        service = build('calendar', 'v3', credentials=creds)

        events_result = service.events().list(
            calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',  
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"Evento: {event['summary']}, Inicio: {start}")
        return events

    def create_event(self, summary, start_time, end_time, timezone, attendees=None):
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        try:
            event = self.service.events().insert(calendarId="primary", body=event).execute()
            print(f"El evento se ha creado con el id: {event.get('htmlLink')}")
        except HttpError as error:
            print(f"An error has occurred: {error}")

    def create_google_calendar_event(self,event_title, start_time):
        print("Procesamos creación de evento")
        start_time_dt = datetime.fromisoformat(start_time)
        end_time_dt = start_time_dt + timedelta(hours=1)
        end_time = end_time_dt.isoformat()

        event = {
            'summary': event_title,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Mexico_City',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Mexico_City',
            },
        }
        
        try:
            print("Procesamos creación de evento TRY")
            created_event = self.service.events().insert(
                calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com', 
                body=event
            ).execute()
        
            return {
            "message": "La operación se completó exitosamente.",
            "data": {
                "appointment_id": created_event.get("id"),
                "summary": created_event.get("summary"),
                "start_time": created_event['start'].get('dateTime'),
                "end_time": created_event['end'].get('dateTime'),
                "htmlLink": created_event.get('htmlLink')
            }
        }

        except Exception as e:
            print(f"Error al crear evento: {str(e)}")
            raise
    
    def update_event(self, event_id, user_name, new_date):
        """
        Actualiza un evento en Google Calendar con una nueva fecha y hora.
        
        Args:
            event_id (str): Identificador único del evento a actualizar.
            user_name (str): Nombre del usuario que solicita el reagendado (opcional, puede ser usado para registrar en 'summary').
            new_date (str): Nueva fecha y hora en formato 'YYYY-MM-DDTHH:mm:ss' (ISO 8601).
            
        Returns:
            dict: Información del evento actualizado.
        """
        try:
            # Obtener el evento existente
            event = self.service.events().get(calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com', eventId=event_id).execute()

            # Calcular la nueva fecha de fin sumándole 1 hora a la fecha de inicio
            start_time_dt = datetime.fromisoformat(new_date)
            end_time_dt = start_time_dt + timedelta(hours=1)

            # Actualizar los datos del evento
            event['start']['dateTime'] = start_time_dt.isoformat()
            event['end']['dateTime'] = end_time_dt.isoformat()

            # Opcional: Personalizar el título del evento con el nombre del usuario
            if user_name:
                event['summary'] = f"Reagendado por {user_name} - {event.get('summary', 'Evento Actualizado')}"

            # Realizar la actualización en Google Calendar
            updated_event = self.service.events().update(
                calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                eventId=event_id,
                body=event
            ).execute()

            print(f"Evento actualizado: {updated_event.get('htmlLink')}")
            # Devolver resultado estandarizado
            return {
                "message": "La operación se completó exitosamente.",
                "data": {
                    "appointment_id": updated_event.get("id"),
                    "summary": updated_event.get("summary"),
                    "start_time": updated_event['start'].get('dateTime'),
                    "end_time": updated_event['end'].get('dateTime'),
                    "htmlLink": updated_event.get('htmlLink')
                }
            }

        except HttpError as error:
            print(f"Error al actualizar el evento: {error}")
            return {"message": "Ocurrió un error al procesar la operación.", "error": str(error)}

        except Exception as e:
            print(f"Error inesperado: {e}")
            return {"message": "Error inesperado al procesar la operación.", "error": str(e)}
        
    def delete_event(self, event_id):
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True

    def update_google_calendar_event_by_details(self,creds, event_title, start_time, updated_title=None, updated_start=None, updated_end=None):
        service = build('calendar', 'v3', credentials=creds)

        try:
            start_datetime = datetime.fromisoformat(start_time)
            time_min = (start_datetime + timedelta(minutes=359)).isoformat() + "Z"
            time_max = (start_datetime + timedelta(minutes=361)).isoformat() + "Z"
            new_start_time = start_datetime.isoformat() + "-06:00"

            if updated_start:
                updated_start_datetime = datetime.fromisoformat(updated_start)
                updated_start = updated_start_datetime.isoformat()
            if updated_end:
                updated_end_datetime = datetime.fromisoformat(updated_end)
                updated_end = updated_end_datetime.isoformat()

            events = self.get_google_calendar_events(creds, time_min, time_max)

            for event in events:
                print(event['start']['dateTime'])
                print(new_start_time)
                if event['summary'] == event_title and event['start']['dateTime'] == new_start_time:
                    if updated_title:
                        event['summary'] = updated_title
                    if updated_start:
                        event['start']['dateTime'] = updated_start
                    if updated_end:
                        event['end']['dateTime'] = updated_end

                    updated_event = service.events().update(
                        calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                        eventId=event['id'],
                        body=event
                    ).execute()

                    print(f"Evento actualizado: {updated_event.get('htmlLink')}")
                    return updated_event

            return {"status": "not_found", "message": f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{new_start_time}'."}

        except Exception as e:
            print(f"Error al actualizar el evento: {str(e)}")
            return {"status": "error", "message": str(e)}

    def delete_google_calendar_event_by_details(creds, event_title, start_time):
        service = build('calendar', 'v3', credentials=creds)

        try:
            start_datetime = datetime.fromisoformat(start_time)
            time_min = (start_datetime - timedelta(minutes=359)).isoformat() + "Z"
            time_max = (start_datetime + timedelta(minutes=361)).isoformat() + "Z"
            start_time_z = (start_datetime).isoformat() +"-06:00"

            events = get_google_calendar_events(creds,time_min, time_max)

            for event in events:
                if event['summary'] == event_title and event['start']['dateTime'] == start_time_z:
                    service.events().delete(
                        calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                        eventId=event['id']
                    ).execute()

                    print(f"Evento eliminado: {event.get('summary')} - {event.get('start')['dateTime']}")
                    return {"status": "success", "message": "Evento eliminado con éxito."}

            return {"status": "not_found", "message": f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{start_time_z}'."}

        except Exception as e:
            print(f"Error al eliminar el evento: {str(e)}")
            return {"status": "error", "message": str(e)}
        
    def get_appointments(self, user_name, service, future_only):
        """
        Obtiene la información de citas agendadas filtradas por usuario, servicio y tiempo.

        Args:
            user_name (str): Nombre del usuario para filtrar las citas.
            service (str): Nombre del servicio para filtrar las citas.
            future_only (bool): Indica si solo se deben devolver citas futuras.

        Returns:
            dict: Lista de citas filtradas o mensaje de error.
        """
        try:
            # Definir los rangos de tiempo para la búsqueda
            now = datetime.now(timezone.utc).isoformat()  # Tiempo actual en formato ISO 8601
            
            print("OBTENEMOS CITAS DEL USUARIO")
            
            # Obtener todas las citas desde Google Calendar
            events_result = self.service.events().list(
                calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                timeMin=now if future_only else None,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            if not events:
                return {
                    "message": "No se encontraron citas agendadas.",
                    "data": []
                }

            # Filtrar eventos basados en 'user_name' y 'service'
            filtered_events = []
            for event in events:
                summary = event.get('summary', '')
                description = event.get('description', '')
                start_time = event['start'].get('dateTime', event['start'].get('date'))
                end_time = event['end'].get('dateTime', event['end'].get('date'))

                # Aplicar filtros de usuario y servicio
                if user_name.lower() in summary.lower() and service.lower() in summary.lower():
                    filtered_events.append({
                        "appointment_id": event.get('id'),
                        "user_name": user_name,
                        "service": service,
                        "start_time": start_time,
                        "end_time": end_time,
                        "description": description,
                        "summary": summary,
                        "location": event.get('location', 'No se proporcionó una ubicación')
                    })
            
            print(filtered_events)

            if not filtered_events:
                return {
                    "message": "No se encontraron citas que coincidan con los filtros especificados.",
                    "data": []
                }

            return {
                "message": "La operación se completó exitosamente.",
                "data": filtered_events
            }

        except HttpError as error:
            print(f"Error al obtener las citas: {error}")
            return {
                "message": "Ocurrió un error al obtener las citas desde Google Calendar.",
                "error": str(error)
            }

        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return {
                "message": "Error inesperado al procesar la operación.",
                "error": str(e)
            }
    
    def cancel_appointment(self, user_name, appointment_datetime, reason=None):
        """
        Cancela una cita agendada en Google Calendar.

        Args:
            user_name (str): Nombre del usuario que desea cancelar la cita.
            appointment_datetime (str): Fecha y hora de la cita a cancelar en formato ISO 8601.
            reason (str): Razón por la cual se cancela la cita (opcional).

        Returns:
            dict: Resultado estandarizado con un mensaje genérico y detalles de la cancelación.
        """
        try:
            # Convertir la fecha y hora de la cita a objeto datetime
            appointment_time = datetime.fromisoformat(appointment_datetime)

            # Definir rangos de tiempo precisos con zona horaria explícita
            time_min = (appointment_time - timedelta(minutes=1)).isoformat()
            time_max = (appointment_time + timedelta(minutes=1)).isoformat()

            # Obtener los eventos en el rango de tiempo
            events_result = self.service.events().list(
                calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                timeMin=f"{time_min}Z",  # Asegura el formato ISO 8601 UTC
                timeMax=f"{time_max}Z",
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            
            print(events)

            # Filtrar el evento por el nombre del usuario
            event_to_delete = None
            for event in events:
                summary = event.get('summary', '')
                start_time = event['start'].get('dateTime', '')

                if user_name.lower() in summary.lower() and start_time.startswith(appointment_datetime):
                    event_to_delete = event
                    break
            
            print("EVENTO A BORRAR")
            print(event_to_delete)

            # Si no se encuentra el evento
            if not event_to_delete:
                return {
                    "message": "No se encontró ninguna cita que coincida con los criterios especificados.",
                    "data": []
                }

            # Eliminar el evento encontrado
            self.service.events().delete(
                calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                eventId=event_to_delete['id']
            ).execute()

            # Opcional: Log de la razón de cancelación
            print(f"Cita cancelada. Razón: {reason}" if reason else "Cita cancelada sin razón especificada.")

            # Devolver respuesta estandarizada
            return {
                "message": "La operación se completó exitosamente. La cita ha sido cancelada.",
                "data": {
                    "appointment_id": event_to_delete['id'],
                    "user_name": user_name,
                    "appointment_datetime": appointment_datetime,
                    "reason": reason if reason else "No especificada",
                    "summary": event_to_delete.get('summary', ''),
                    "status": "cancelled"
                }
            }

        except HttpError as error:
            print(f"Error al cancelar la cita: {error}")
            return {
                "message": "Ocurrió un error al cancelar la cita.",
                "error": str(error)
            }

        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return {
                "message": "Error inesperado al procesar la operación.",
                "error": str(e)
            }
