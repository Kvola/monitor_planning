{
    'name': 'Système de Planification des Moniteurs',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Gestion complète de la planification des moniteurs d\'école du dimanche',
    'description': """
Système de Planification des Moniteurs
======================================

Ce module fournit un système complet pour la gestion de la planification des moniteurs d'école du dimanche :

Fonctionnalités principales :
-----------------------------
* **Modèles de planification** : Créez des modèles récurrents (hebdomadaire, mensuel, etc.)
* **Planification automatique** : Génération automatique des plannings selon les modèles
* **Rotation des moniteurs** : Système de rotation équitable entre les moniteurs
* **Gestion des remplacements** : Système de remplacement avec notifications
* **Suivi des disponibilités** : Les moniteurs peuvent déclarer leurs disponibilités
* **Évaluations** : Système d'évaluation périodique des moniteurs
* **Formations** : Gestion des formations et certifications
* **Rapports d'activité** : Rapports périodiques des moniteurs
* **Notifications automatiques** : Rappels et confirmations automatiques
* **Tableau de bord** : Statistiques et analyses des activités
    """,
    'author': 'Votre Nom',
    'website': 'https://www.example.com',
    'depends': [
        'base',
        'mail',
        'calendar',
        'hr',
        'random_team_generator',  # Assurez-vous que ce module est installé
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/monitor_certificate_views.xml',  # Loaded before monitor_training_views.xml
        'views/monitor_training_views.xml',
        'views/monitor_availability_views.xml',
        'views/monitor_evaluation_views.xml',
        'views/monitor_report_views.xml',
        'views/monitor_planning_template_views.xml',
        'views/monitor_planning_views.xml',
        'wizards/monitor_substitute_wizard_views.xml',
        'reports/monitor_planning.xml',
        'views/menu_views.xml',
        'views/monitor_template_views.xml',
    ],
    'demo': [
        'demo/monitor_planning_demo.xml',
    ],
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}