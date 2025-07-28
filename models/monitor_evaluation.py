from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorEvaluation(models.Model):
    """Évaluation des moniteurs"""
    _name = "monitor.evaluation"
    _description = "Évaluation moniteur"
    _order = "evaluation_date desc"

    monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur évalué",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    evaluator_id = fields.Many2one(
        'res.partner',
        string="Évaluateur",
        required=True,
        default=lambda self: self.env.user.partner_id
    )
    
    evaluation_date = fields.Date(
        string="Date d'évaluation",
        required=True,
        default=fields.Date.today
    )
    
    period_from = fields.Date(string="Période évaluée du", required=True)
    period_to = fields.Date(string="Au", required=True)
    
    # Critères d'évaluation
    punctuality = fields.Selection([
        ('1', 'Très insuffisant'),
        ('2', 'Insuffisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Ponctualité", required=True)
    
    preparation = fields.Selection([
        ('1', 'Très insuffisant'),
        ('2', 'Insuffisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Préparation", required=True)
    
    teaching_quality = fields.Selection([
        ('1', 'Très insuffisant'),
        ('2', 'Insuffisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Qualité d'enseignement", required=True)
    
    child_interaction = fields.Selection([
        ('1', 'Très insuffisant'),
        ('2', 'Insuffisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Interaction avec les enfants", required=True)
    
    creativity = fields.Selection([
        ('1', 'Très insuffisant'),
        ('2', 'Insuffisant'),
        ('3', 'Correct'),
        ('4', 'Bien'),
        ('5', 'Excellent')
    ], string="Créativité", required=True)
    
    # Note globale calculée
    overall_rating = fields.Float(
        string="Note globale",
        compute="_compute_overall_rating",
        store=True
    )
    
    # Commentaires
    strengths = fields.Text(string="Points forts")
    areas_for_improvement = fields.Text(string="Points d'amélioration")
    recommendations = fields.Text(string="Recommandations")
    
    # Suivi
    follow_up_required = fields.Boolean(string="Suivi nécessaire")
    follow_up_date = fields.Date(string="Date de suivi")
    follow_up_notes = fields.Text(string="Notes de suivi")
    
    @api.depends('punctuality', 'preparation', 'teaching_quality', 'child_interaction', 'creativity')
    def _compute_overall_rating(self):
        for evaluation in self:
            ratings = [
                int(evaluation.punctuality or 0),
                int(evaluation.preparation or 0),
                int(evaluation.teaching_quality or 0),
                int(evaluation.child_interaction or 0),
                int(evaluation.creativity or 0)
            ]
            if all(ratings):
                evaluation.overall_rating = sum(ratings) / len(ratings)
            else:
                evaluation.overall_rating = 0.0
    
    @api.constrains('period_from', 'period_to')
    def _check_period_dates(self):
        for evaluation in self:
            if evaluation.period_from > evaluation.period_to:
                raise ValidationError("La date de début de période doit être antérieure à la date de fin.")