export function isValidRegistrationPassword(password: string): boolean {
  return password.length >= 12 && password.length <= 200 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password);
}