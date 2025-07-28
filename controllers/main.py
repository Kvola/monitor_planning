from odoo import http, fields
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

class MonitorPlanningController(http.Controller):
    
    @http.route([
        '/monitor/planning',
        '/monitor/planning/<string:view_type>',
        '/monitor/planning/<string:view_type>/<string:date_filter>'
    ], type='http', auth="public", website=True)
    def monitor_planning_view(self, view_type='week', date_filter=None, **kw):
        """Vue principale de la planification des moniteurs"""
        
        # Récupérer les paramètres de la requête
        start_date = kw.get('start_date')
        end_date = kw.get('end_date')
        school_id = kw.get('school_id')
        monitor_id = kw.get('monitor_id')
        
        # Calculer les dates selon le type de vue
        today = fields.Date.today()
        
        if view_type == 'week':
            if start_date:
                start = fields.Date.from_string(start_date)
            else:
                # Début de la semaine (lundi)
                start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            title = f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}"
            
        elif view_type == 'month':
            if start_date:
                start = fields.Date.from_string(start_date)
                start = start.replace(day=1)
            else:
                start = today.replace(day=1)
            end = start + relativedelta(months=1) - timedelta(days=1)
            title = f"Mois de {start.strftime('%B %Y')}"
            
        else:  # custom period
            if start_date and end_date:
                start = fields.Date.from_string(start_date)
                end = fields.Date.from_string(end_date)
            else:
                start = today
                end = today + timedelta(days=30)
            title = f"Période du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}"
        
        # Construire le domaine de recherche
        domain = [
            ('planned_date', '>=', start),
            ('planned_date', '<=', end),
        ]
        
        if school_id:
            domain.append(('school_id', '=', int(school_id)))
        
        if monitor_id:
            domain.append(('monitor_id', '=', int(monitor_id)))
        
        # Récupérer les données
        plannings = request.env['monitor.planning'].sudo().search(domain, order='planned_date, start_time')
        schools = request.env['res.partner'].sudo().search([('organization_type', '=', 'school')])
        monitors = request.env['res.partner'].sudo().search([('is_monitor', '=', True)])
        
        # Organiser les données par date pour l'affichage
        planning_by_date = {}
        for planning in plannings:
            date_str = planning.planned_date.strftime('%Y-%m-%d')
            if date_str not in planning_by_date:
                planning_by_date[date_str] = []
            planning_by_date[date_str].append(planning)
        
        # Créer la liste des jours à afficher
        current_date = start
        days_list = []
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            days_list.append({
                'date': current_date,
                'date_str': date_str,
                'plannings': planning_by_date.get(date_str, []),
                'day_name': current_date.strftime('%A'),
                'day_number': current_date.day,
                'is_today': current_date == today,
                'is_weekend': current_date.weekday() >= 5
            })
            current_date += timedelta(days=1)
        
        # Navigation
        if view_type == 'week':
            prev_start = start - timedelta(days=7)
            next_start = start + timedelta(days=7)
        elif view_type == 'month':
            prev_start = start - relativedelta(months=1)
            next_start = start + relativedelta(months=1)
        else:
            delta = end - start
            prev_start = start - delta
            next_start = end + timedelta(days=1)
        
        # Statistiques rapides
        stats = {
            'total_plannings': len(plannings),
            'confirmed': len(plannings.filtered(lambda p: p.state == 'confirmed')),
            'completed': len(plannings.filtered(lambda p: p.state == 'completed')),
            'cancelled': len(plannings.filtered(lambda p: p.state == 'cancelled')),
            'overdue': len(plannings.filtered(lambda p: p.is_overdue)),
        }
        
        values = {
            'plannings': plannings,
            'days_list': days_list,
            'schools': schools,
            'monitors': monitors,
            'view_type': view_type,
            'start_date': start,
            'end_date': end,
            'title': title,
            'prev_start': prev_start,
            'next_start': next_start,
            'current_school_id': int(school_id) if school_id else None,
            'current_monitor_id': int(monitor_id) if monitor_id else None,
            'stats': stats,
            'today': today,
        }
        
        return request.render('monitor_planning.planning_view', values)
    
    @http.route('/monitor/planning/json', type='json', auth="public", website=True)
    def get_planning_data(self, **kw):
        """API JSON pour récupérer les données de planification"""
        
        start_date = kw.get('start_date')
        end_date = kw.get('end_date')
        school_id = kw.get('school_id')
        monitor_id = kw.get('monitor_id')
        
        domain = []
        
        if start_date:
            domain.append(('planned_date', '>=', start_date))
        if end_date:
            domain.append(('planned_date', '<=', end_date))
        if school_id:
            domain.append(('school_id', '=', school_id))
        if monitor_id:
            domain.append(('monitor_id', '=', monitor_id))
        
        plannings = request.env['monitor.planning'].sudo().search(domain)
        
        data = []
        for planning in plannings:
            data.append({
                'id': planning.id,
                'name': planning.name,
                'monitor_name': planning.monitor_id.name,
                'school_name': planning.school_id.name,
                'planned_date': planning.planned_date.strftime('%Y-%m-%d'),
                'start_time': planning.start_time,
                'end_time': planning.end_time,
                'state': planning.state,
                'topic': planning.topic or '',
                'expected_participants': planning.expected_participants,
                'actual_participants': planning.actual_participants,
            })
        
        return {'plannings': data}
    
    @http.route('/monitor/planning/calendar', type='http', auth="public", website=True)
    def planning_calendar(self, **kw):
        """Vue calendrier des planifications"""
        
        # Récupérer le mois et l'année
        year = int(kw.get('year', datetime.now().year))
        month = int(kw.get('month', datetime.now().month))
        
        # Premier et dernier jour du mois
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Étendre pour inclure les jours de la semaine
        start_calendar = start_date - timedelta(days=start_date.weekday())
        end_calendar = end_date + timedelta(days=6 - end_date.weekday())
        
        # Récupérer les planifications
        plannings = request.env['monitor.planning'].sudo().search([
            ('planned_date', '>=', start_calendar),
            ('planned_date', '<=', end_calendar)
        ])
        
        # Organiser par date
        planning_by_date = {}
        for planning in plannings:
            date_str = planning.planned_date.strftime('%Y-%m-%d')
            if date_str not in planning_by_date:
                planning_by_date[date_str] = []
            planning_by_date[date_str].append(planning)
        
        # Créer le calendrier
        calendar_data = []
        current_date = start_calendar
        
        while current_date <= end_calendar:
            week_data = []
            for i in range(7):  # 7 jours de la semaine
                date_str = current_date.strftime('%Y-%m-%d')
                week_data.append({
                    'date': current_date,
                    'date_str': date_str,
                    'day': current_date.day,
                    'plannings': planning_by_date.get(date_str, []),
                    'is_current_month': current_date.month == month,
                    'is_today': current_date == datetime.now().date(),
                    'is_weekend': current_date.weekday() >= 5
                })
                current_date += timedelta(days=1)
            calendar_data.append(week_data)
            
            if current_date > end_calendar:
                break
        
        # Navigation
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        values = {
            'calendar_data': calendar_data,
            'current_month': month,
            'current_year': year,
            'month_name': start_date.strftime('%B'),
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'weekdays': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
        }
        
        return request.render('monitor_planning.calendar_view', values)
    
    @http.route('/monitor/planning/details/<int:planning_id>', type='http', auth="public", website=True)
    def planning_details(self, planning_id, **kw):
        """Détails d'une planification"""
        
        planning = request.env['monitor.planning'].sudo().browse(planning_id)
        
        if not planning.exists():
            return request.render('website.404')
        
        values = {
            'planning': planning,
        }
        
        return request.render('monitor_planning.planning_details', values)