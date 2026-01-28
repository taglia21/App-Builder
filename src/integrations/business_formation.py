import os
import httpx
from typing import Dict, Optional
from datetime import datetime

class BusinessFormationService:
    """Business formation service integrating with Stripe Atlas and legal services."""
    
    def __init__(self):
        self.stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        
    async def start_atlas_application(self, business_info: Dict) -> Dict:
        """Initiate Stripe Atlas business formation (redirects to Atlas)."""
        # Stripe Atlas requires manual application - we prepare the data
        atlas_data = {
            'company_name': business_info.get('company_name'),
            'business_type': business_info.get('business_type', 'llc'),
            'state': business_info.get('state', 'DE'),
            'industry': business_info.get('industry'),
            'founder_info': business_info.get('founders', []),
            'application_url': 'https://stripe.com/atlas'
        }
        
        return {
            'success': True,
            'message': 'Atlas application prepared',
            'redirect_url': 'https://stripe.com/atlas',
            'prepared_data': atlas_data
        }
    
    async def register_llc(self, company_name: str, state: str, owner_info: Dict) -> Dict:
        """Register an LLC (simulated with state API integration)."""
        # This would integrate with state-specific APIs
        registration = {
            'company_name': company_name,
            'state': state,
            'type': 'LLC',
            'status': 'pending',
            'owner': owner_info,
            'filed_date': datetime.utcnow().isoformat(),
            'estimated_completion': '3-5 business days',
            'next_steps': [
                'Await state confirmation',
                'Receive EIN from IRS',
                'Set up business bank account',
                'Configure payment processing'
            ]
        }
        
        return {'success': True, 'registration': registration}
    
    async def get_ein_application_info(self) -> Dict:
        """Get information for EIN application."""
        return {
            'success': True,
            'irs_url': 'https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online',
            'requirements': [
                'Legal business name',
                'Business address',
                'Responsible party SSN/ITIN',
                'Business start date',
                'Principal business activity'
            ],
            'processing_time': 'Immediate (online application)'
        }
    
    async def create_operating_agreement(self, company_info: Dict) -> Dict:
        """Generate LLC operating agreement template."""
        template = f'''LLC OPERATING AGREEMENT
OF {company_info.get("company_name", "[COMPANY NAME]").upper()}

This Operating Agreement ("Agreement") is entered into as of {datetime.utcnow().strftime("%B %d, %Y")}

ARTICLE I - FORMATION
The Members hereby form a Limited Liability Company under the laws of {company_info.get("state", "Delaware")}.

ARTICLE II - NAME
The name of the Company shall be: {company_info.get("company_name", "[COMPANY NAME]")}

ARTICLE III - PURPOSE
The purpose of the Company is to engage in any lawful business activity.

ARTICLE IV - MEMBERS AND CAPITAL
Initial Members and their respective ownership interests:
'''
        
        for member in company_info.get('members', [{'name': 'Founder', 'percentage': 100}]):
            template += f"- {member['name']}: {member['percentage']}%\n"
        
        template += '''
ARTICLE V - MANAGEMENT
The Company shall be managed by its Members.

ARTICLE VI - DISTRIBUTIONS
Distributions shall be made in proportion to ownership interests.

[SIGNATURES REQUIRED]
'''
        
        return {
            'success': True,
            'document': template,
            'document_type': 'Operating Agreement',
            'requires_signature': True
        }
    
    async def setup_stripe_connect(self, business_id: str, business_info: Dict) -> Dict:
        """Set up Stripe Connect for the new business."""
        if not self.stripe_key:
            return {'success': False, 'error': 'Stripe not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://api.stripe.com/v1/accounts',
                    headers={
                        'Authorization': f'Bearer {self.stripe_key}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    data={
                        'type': 'express',
                        'country': 'US',
                        'email': business_info.get('email'),
                        'capabilities[card_payments][requested]': 'true',
                        'capabilities[transfers][requested]': 'true',
                        'business_type': 'company',
                        'company[name]': business_info.get('company_name')
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': True,
                        'account_id': data.get('id'),
                        'onboarding_url': await self._create_account_link(data.get('id'))
                    }
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _create_account_link(self, account_id: str) -> str:
        """Create Stripe Connect onboarding link."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://api.stripe.com/v1/account_links',
                    headers={
                        'Authorization': f'Bearer {self.stripe_key}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    data={
                        'account': account_id,
                        'refresh_url': os.environ.get('APP_URL', 'https://launchforge.up.railway.app') + '/business/refresh',
                        'return_url': os.environ.get('APP_URL', 'https://launchforge.up.railway.app') + '/business/complete',
                        'type': 'account_onboarding'
                    }
                )
                if response.status_code == 200:
                    return response.json().get('url')
                return None
        except Exception:
            return None
    
    async def get_business_checklist(self, business_type: str = 'llc') -> Dict:
        """Get business formation checklist."""
        checklist = {
            'llc': [
                {'step': 'Choose a business name', 'status': 'pending', 'required': True},
                {'step': 'File Articles of Organization', 'status': 'pending', 'required': True},
                {'step': 'Create Operating Agreement', 'status': 'pending', 'required': True},
                {'step': 'Obtain EIN from IRS', 'status': 'pending', 'required': True},
                {'step': 'Open business bank account', 'status': 'pending', 'required': True},
                {'step': 'Set up payment processing', 'status': 'pending', 'required': True},
                {'step': 'Register for state taxes', 'status': 'pending', 'required': True},
                {'step': 'Obtain business licenses', 'status': 'pending', 'required': False}
            ],
            'corporation': [
                {'step': 'Choose a business name', 'status': 'pending', 'required': True},
                {'step': 'File Articles of Incorporation', 'status': 'pending', 'required': True},
                {'step': 'Create Bylaws', 'status': 'pending', 'required': True},
                {'step': 'Issue stock certificates', 'status': 'pending', 'required': True},
                {'step': 'Hold initial board meeting', 'status': 'pending', 'required': True},
                {'step': 'Obtain EIN from IRS', 'status': 'pending', 'required': True},
                {'step': 'Open business bank account', 'status': 'pending', 'required': True}
            ]
        }
        
        return {'success': True, 'checklist': checklist.get(business_type, checklist['llc'])}
