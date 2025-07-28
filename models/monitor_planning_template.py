from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar


class MonitorPlanningTemplate(models.Model):
    """Modèle pour les modèles de planification récurrente"""
    _name = "monitor.planning.template"
    _description = "Modèle de planification des moniteurs"
    _order = "name"

    name = fields.Char(string="Nom du modèle", required=True)
    description = fields.Text(string="Description")
    
    # École associée
    school_id = fields.Many2one(
        'res.partner',
        string="École",
        domain="[('organization_type', '=', 'school')]",
        required=True
    )
    
    # Récurrence
    recurrence_type = fields.Selection([
        ('weekly', 'Hebdomadaire'),
        ('biweekly', 'Bi-hebdomadaire'),
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('custom', 'Personnalisé')
    ], string="Type de récurrence", default='weekly', required=True)
    
    # Pour récurrence hebdomadaire/bi-hebdomadaire
    weekday = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche')
    ], string="Jour de la semaine")
    
    # Pour récurrence mensuelle
    monthly_type = fields.Selection([
        ('date', 'Date fixe'),
        ('weekday', 'Jour de la semaine')
    ], string="Type mensuel", default='date')
    
    monthly_date = fields.Integer(string="Date du mois", default=1)
    monthly_week = fields.Selection([
        ('1', 'Premier'),
        ('2', 'Deuxième'),
        ('3', 'Troisième'),
        ('4', 'Quatrième'),
        ('-1', 'Dernier')
    ], string="Semaine du mois")
    
    # Pour récurrence personnalisée
    custom_interval = fields.Integer(string="Intervalle (jours)", default=7)
    
    # Horaires
    start_time = fields.Float(string="Heure de début", default=9.0)
    end_time = fields.Float(string="Heure de fin", default=11.0)
    
    # Période d'activité
    active_from = fields.Date(string="Actif à partir de", default=fields.Date.today)
    active_until = fields.Date(string="Actif jusqu'au")
    
    # Moniteurs assignés par rotation
    monitor_rotation_ids = fields.One2many(
        'monitor.rotation.line',
        'template_id',
        string="Rotation des moniteurs"
    )
    
    # Statut
    active = fields.Boolean(string="Actif", default=True)
    
    # Planifications générées
    planning_ids = fields.One2many(
        'monitor.planning',
        'template_id',
        string="Planifications générées"
    )
    
    planning_count = fields.Integer(
        string="Nombre de planifications",
        compute="_compute_planning_count"
    )
    
    @api.depends('planning_ids')
    def _compute_planning_count(self):
        for template in self:
            template.planning_count = len(template.planning_ids)
    
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for template in self:
            if template.start_time >= template.end_time:
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")
    
    @api.constrains('active_from', 'active_until')
    def _check_dates(self):
        for template in self:
            if template.active_until and template.active_from > template.active_until:
                raise ValidationError("La date de début doit être antérieure à la date de fin.")
    
    @api.constrains('monthly_date')
    def _check_monthly_date(self):
        for template in self:
            if template.recurrence_type == 'monthly' and template.monthly_type == 'date':
                if not (1 <= template.monthly_date <= 31):
                    raise ValidationError("La date du mois doit être entre 1 et 31.")
    
    def generate_plannings_next_period(self):
        """Génère les planifications pour la prochaine période"""
        self.ensure_one()
        
        # Définir la période à générer (par exemple, les 3 prochains mois)
        start_date = fields.Date.today()
        if self.recurrence_type == 'weekly':
            end_date = start_date + relativedelta(months=3)
        elif self.recurrence_type == 'biweekly':
            end_date = start_date + relativedelta(months=3)
        elif self.recurrence_type == 'monthly':
            end_date = start_date + relativedelta(months=6)
        elif self.recurrence_type == 'quarterly':
            end_date = start_date + relativedelta(years=1)
        else:  # custom
            end_date = start_date + relativedelta(months=6)
        
        return self.generate_plannings(start_date, end_date)
    
    def generate_plannings(self, start_date, end_date):
        """Génère les planifications pour une période donnée"""
        self.ensure_one()
        
        if not self.monitor_rotation_ids:
            raise UserError("Aucun moniteur n'est configuré dans la rotation.")
        
        plannings_created = []
        current_date = self._get_next_occurrence(start_date)
        monitor_index = 0
        
        while current_date and current_date <= end_date:
            # Vérifier si le modèle est encore actif à cette date
            if self.active_until and current_date > self.active_until:
                break
            
            # Vérifier s'il n'existe pas déjà une planification pour cette date
            existing = self.env['monitor.planning'].search([
                ('template_id', '=', self.id),
                ('planned_date', '=', current_date)
            ], limit=1)
            
            if not existing:
                # Obtenir le moniteur selon la rotation
                rotation_line = self.monitor_rotation_ids[monitor_index % len(self.monitor_rotation_ids)]
                
                planning = self.env['monitor.planning'].create({
                    'name': f"{self.name} - {current_date.strftime('%d/%m/%Y')}",
                    'template_id': self.id,
                    'school_id': self.school_id.id,
                    'monitor_id': rotation_line.monitor_id.id,
                    'planned_date': current_date,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'state': 'planned'
                })
                plannings_created.append(planning)
                monitor_index += 1
            
            # Calculer la prochaine occurrence
            current_date = self._get_next_occurrence(current_date + timedelta(days=1))
        
        return plannings_created
    
    def _get_next_occurrence(self, from_date):
        """Calcule la prochaine occurrence selon le type de récurrence"""
        self.ensure_one()
        
        if self.recurrence_type == 'weekly':
            return self._get_next_weekday(from_date, int(self.weekday))
        elif self.recurrence_type == 'biweekly':
            next_week = self._get_next_weekday(from_date, int(self.weekday))
            # Pour bi-hebdomadaire, on prend une semaine sur deux
            return next_week
        elif self.recurrence_type == 'monthly':
            return self._get_next_monthly(from_date)
        elif self.recurrence_type == 'quarterly':
            return self._get_next_quarterly(from_date)
        elif self.recurrence_type == 'custom':
            return from_date + timedelta(days=self.custom_interval)
        
        return None
    
    def _get_next_weekday(self, from_date, weekday):
        """Trouve le prochain jour de la semaine spécifié"""
        days_ahead = weekday - from_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return from_date + timedelta(days=days_ahead)
    
    def _get_next_monthly(self, from_date):
        """Trouve la prochaine occurrence mensuelle"""
        if self.monthly_type == 'date':
            # Date fixe du mois
            try:
                next_month = from_date.replace(day=self.monthly_date)
                if next_month <= from_date:
                    if from_date.month == 12:
                        next_month = next_month.replace(year=from_date.year + 1, month=1)
                    else:
                        next_month = next_month.replace(month=from_date.month + 1)
                return next_month
            except ValueError:
                # Date invalide (ex: 31 dans un mois de 30 jours)
                next_month = from_date.replace(day=1) + relativedelta(months=1)
                try:
                    return next_month.replace(day=self.monthly_date)
                except ValueError:
                    # Prendre le dernier jour du mois
                    last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                    return next_month.replace(day=last_day)
        else:
            # Jour de la semaine spécifique
            return self._get_next_monthly_weekday(from_date)
    
    def _get_next_monthly_weekday(self, from_date):
        """Trouve le prochain jour de la semaine mensuel (ex: premier lundi du mois)"""
        # Implémentation simplifiée - à développer selon les besoins
        next_month = from_date.replace(day=1) + relativedelta(months=1)
        return self._get_next_weekday(next_month, int(self.weekday))
    
    def _get_next_quarterly(self, from_date):
        """Trouve la prochaine occurrence trimestrielle"""
        next_quarter = from_date + relativedelta(months=3)
        return self._get_next_weekday(next_quarter, int(self.weekday or '6'))  # Dimanche par défaut
    
    def action_view_plannings(self):
        """Action pour voir les planifications générées"""
        return {
            'name': f'Planifications - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'monitor.planning',
            'view_mode': 'calendar,tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {
                'default_template_id': self.id,
                'default_school_id': self.school_id.id
            }
        }