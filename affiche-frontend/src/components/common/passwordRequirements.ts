export const MIN_PASSWORD_LENGTH = 8;

export interface PasswordRule {
  label: string;
  met: boolean;
}

export function passwordRules(password: string, confirm: string): PasswordRule[] {
  return [
    { label: `At least ${MIN_PASSWORD_LENGTH} characters`, met: password.length >= MIN_PASSWORD_LENGTH },
    { label: 'Both passwords match', met: password.length > 0 && password === confirm },
  ];
}
