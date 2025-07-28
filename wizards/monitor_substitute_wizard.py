from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import calendar

class MonitorSubstituteWizard(models.TransientModel):
    """Assistant pour demander un remplaçant"""
    _name = "monitor.substitute.wizard"
    _description = "Assistant remplaçant moniteur"

    planning_id = fields.Many2one(
        'monitor.planning',
        string="Planification",
        required=True
    )
    
    school_id = fields.Many2one(
        'res.partner',
        string="École",
        related='planning_id.school_id',
        readonly=True
    )
    
    substitute_monitor_id = fields.Many2one(
        'res.partner',
        string="Moniteur remplaçant",
        domain="[('is_monitor', '=', True)]",
        required=True
    )
    
    reason = fields.Text(string="Raison du remplacement", required=True)
    
    notify_substitute = fields.Boolean(
        string="Notifier le remplaçant",
        default=True
    )
    
    def action_assign_substitute(self):
        """Assigne le remplaçant"""
        self.ensure_one()
        
        # Mettre à jour la planification
        self.planning_id.substitute_monitor_id = self.substitute_monitor_id.id
        
        # Créer une note dans le chatter
        message = f"""
        Remplaçant assigné : {self.substitute_monitor_id.name}
        Moniteur original : {self.planning_id.monitor_id.name}
        Raison : {self.reason}
        """
        self.planning_id.message_post(body=message)
        
        # Notifier le remplaçant si demandé
        if self.notify_substitute:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': f'Remplacement - {self.planning_id.display_name}',
                'note': f'''
                    Bonjour {self.substitute_monitor_id.name},
                    
                    Vous avez été désigné(e) pour remplacer {self.planning_id.monitor_id.name} :
                    
                    - École : {self.school_id.name}
                    - Date : {self.planning_id.planned_date.strftime("%d/%m/%Y")}
                    - Horaire : {self.planning_id._format_time(self.planning_id.start_time)} - {self.planning_id._format_time(self.planning_id.end_time)}
                    - Sujet : {self.planning_id.topic or 'À définir'}
                    
                    Raison du remplacement : {self.reason}
                    
                    Merci de confirmer votre disponibilité.
                ''',
                'user_id': self.env.user.id,
                'res_id': self.substitute_monitor_id.id,
                'res_model_id': self.env['ir.model']._get('res.partner').id,
                'date_deadline': self.planning_id.planned_date - timedelta(days=1),
            })
        
        return {'type': 'ir.actions.act_window_close'}