from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from busstops.models import FeatureToggle


class Command(BaseCommand):
    help = 'Manage feature toggles from the command line'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # List features
        list_parser = subparsers.add_parser('list', help='List all feature toggles')
        list_parser.add_argument('--status', choices=['enabled', 'disabled', 'maintenance', 'all'], 
                               default='all', help='Filter by status')
        
        # Enable maintenance mode
        maintenance_parser = subparsers.add_parser('maintenance', help='Enable/disable maintenance mode')
        maintenance_parser.add_argument('action', choices=['on', 'off'], help='Turn maintenance on or off')
        maintenance_parser.add_argument('--feature', default='site_maintenance', 
                                      help='Feature name (default: site_maintenance)')
        maintenance_parser.add_argument('--hours', type=int, default=2, 
                                      help='Estimated hours for maintenance (default: 2)')
        maintenance_parser.add_argument('--message', 
                                      help='Custom maintenance message')
        
        # Toggle feature
        toggle_parser = subparsers.add_parser('toggle', help='Toggle a specific feature')
        toggle_parser.add_argument('feature_name', help='Name of the feature to toggle')
        toggle_parser.add_argument('--enable', action='store_true', help='Enable the feature')
        toggle_parser.add_argument('--disable', action='store_true', help='Disable the feature')
        toggle_parser.add_argument('--maintenance', action='store_true', help='Put in maintenance mode')
        toggle_parser.add_argument('--superuser-only', action='store_true', help='Make superuser only')
        
        # Create feature
        create_parser = subparsers.add_parser('create', help='Create a new feature toggle')
        create_parser.add_argument('name', help='Feature name')
        create_parser.add_argument('--enabled', action='store_true', default=True, help='Enable by default')
        create_parser.add_argument('--maintenance', action='store_true', help='Start in maintenance mode')
        create_parser.add_argument('--superuser-only', action='store_true', help='Superuser only')

    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'manage_features')
            return
            
        if action == 'list':
            self.list_features(options['status'])
        elif action == 'maintenance':
            self.handle_maintenance(options)
        elif action == 'toggle':
            self.toggle_feature(options)
        elif action == 'create':
            self.create_feature(options)

    def list_features(self, status_filter):
        """List all feature toggles"""
        features = FeatureToggle.objects.all()
        
        if status_filter != 'all':
            if status_filter == 'enabled':
                features = features.filter(enabled=True, maintenance=False)
            elif status_filter == 'disabled':
                features = features.filter(enabled=False)
            elif status_filter == 'maintenance':
                features = features.filter(maintenance=True)
        
        if not features.exists():
            self.stdout.write(self.style.WARNING('No feature toggles found.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'\nFeature Toggles ({status_filter}):'))
        self.stdout.write('-' * 80)
        
        for feature in features:
            status_color = self.style.SUCCESS if feature.enabled and not feature.maintenance else self.style.ERROR
            if feature.maintenance:
                status_color = self.style.WARNING
                
            self.stdout.write(f'{feature.name:<30} {status_color(feature.status_text):<20} Updated: {feature.updated_at.strftime("%Y-%m-%d %H:%M")}')
            
            if feature.maintenance_message:
                self.stdout.write(f'  Message: {feature.maintenance_message}')
            if feature.estimated_hours:
                self.stdout.write(f'  Estimated hours: {feature.estimated_hours}')

    def handle_maintenance(self, options):
        """Handle maintenance mode on/off"""
        feature_name = options['feature']
        action = options['action']
        
        try:
            feature, created = FeatureToggle.objects.get_or_create(
                name=feature_name,
                defaults={
                    'enabled': True,
                    'maintenance': False,
                }
            )
            
            if action == 'on':
                feature.maintenance = True
                feature.enabled = True
                feature.estimated_hours = options['hours']
                if options['message']:
                    feature.maintenance_message = options['message']
                feature.save()
                
                # Clear cache to ensure immediate effect
                cache.delete('site_maintenance_feature')
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Maintenance mode enabled for "{feature_name}"')
                )
                self.stdout.write(f'  Estimated duration: {options["hours"]} hours')
                if options['message']:
                    self.stdout.write(f'  Message: {options["message"]}')
                    
            elif action == 'off':
                feature.maintenance = False
                feature.save()
                
                # Clear cache to ensure immediate effect
                cache.delete('site_maintenance_feature')
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Maintenance mode disabled for "{feature_name}"')
                )
                
        except Exception as e:
            raise CommandError(f'Error managing maintenance mode: {e}')

    def toggle_feature(self, options):
        """Toggle a specific feature"""
        feature_name = options['feature_name']
        
        try:
            feature = FeatureToggle.objects.get(name=feature_name)
        except FeatureToggle.DoesNotExist:
            raise CommandError(f'Feature "{feature_name}" does not exist. Use "create" command first.')
        
        if options['enable']:
            feature.enabled = True
            feature.maintenance = False
        elif options['disable']:
            feature.enabled = False
        elif options['maintenance']:
            feature.maintenance = True
            feature.enabled = True
        
        if options['superuser_only']:
            feature.super_user_only = True
            
        feature.save()
        
        # Clear cache
        cache.delete('site_maintenance_feature')
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Feature "{feature_name}" updated: {feature.status_text}')
        )

    def create_feature(self, options):
        """Create a new feature toggle"""
        name = options['name']
        
        try:
            feature, created = FeatureToggle.objects.get_or_create(
                name=name,
                defaults={
                    'enabled': options['enabled'],
                    'maintenance': options['maintenance'],
                    'super_user_only': options['superuser_only'],
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created feature toggle "{name}" - {feature.status_text}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Feature toggle "{name}" already exists - {feature.status_text}')
                )
                
        except Exception as e:
            raise CommandError(f'Error creating feature: {e}')
