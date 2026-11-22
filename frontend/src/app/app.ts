
import { CommonModule } from '@angular/common';
import {
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';

type AuthView =
  | 'login'
  | 'register'
  | 'verify'
  | 'payment'
  | 'payment-success'
  | 'forgot'
  | 'reset';

interface PaymentReceipt {
  member_id: string;
  receipt_number: string;
  payment_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  payment_status: string;
  receipt_email_sent: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit, OnDestroy {
  private readonly API = 'http://localhost:8000';
  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  email = '';
  password = '';
  token = '';
  role = '';
  page = 'books';
  loading = false;
  restoringSession = false;
  message = '';
  search = '';

  authView: AuthView = 'login';
  authNotice = '';
  authError = '';

  registration = {
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  };

  registrationEmail = '';
  verificationOtp = '';

  paymentMethod: 'UPI' | 'CARD' | 'NET_BANKING' = 'UPI';
  paymentReceipt: PaymentReceipt | null = null;

  resetEmail = '';
  resetOtp = '';
  newPassword = '';
  confirmNewPassword = '';

  books: any[] = [];
  dashboard: any = null;
  reservations: any[] = [];
  fines: any[] = [];
  checkoutRequests: any[] = [];
  myCheckoutRequests: any[] = [];

  newBook = {
    title: '',
    author: '',
    total_copies: 1
  };

  editingBookId = '';
  editBook = { title: '', author: '' };
  copiesBookId = '';
  copiesQuantity = 1;

  // ============================================
  // BOOK COVER CACHE
  // ============================================

  private readonly bookCoverCache = new Map<string, string>();
  private readonly bookCoverLoading = new Set<string>();

  constructor(
    private http: HttpClient,
    private auth: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  // ============================================
  // LIFECYCLE
  // ============================================

  ngOnInit(): void {
    if (
      sessionStorage.getItem('library_tab_session') !== 'active'
    ) {
      return;
    }

    this.restoringSession = true;

    this.auth.restoreSession().subscribe({
      next: () => this.initializeSession(),
      error: () => {
        this.resetInterface();
        this.cdr.detectChanges();
      }
    });
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
  }

  // ============================================
  // ERROR HANDLING
  // ============================================

  private errorText(error: any, fallback: string): string {
    const detail = error?.error?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail.map((item: any) => item.msg).join('; ');
    }

    return fallback;
  }

  private authFailure(error: any, fallback: string): void {
    this.authError = this.errorText(error, fallback);
    this.loading = false;
    this.cdr.detectChanges();
  }

  // ============================================
  // AUTH VIEW
  // ============================================

  changeAuthView(view: AuthView): void {
    this.authView = view;
    this.authNotice = '';
    this.authError = '';
    this.message = '';
    this.cdr.detectChanges();
  }

  // ============================================
  // MEMBER REGISTRATION
  // ============================================

  registerMember(): void {
    this.authError = '';
    this.authNotice = '';

    if (
      !this.registration.name.trim() ||
      !this.registration.email.trim() ||
      !this.registration.password
    ) {
      this.authError = 'Please fill in all registration fields.';
      return;
    }

    if (
      this.registration.password !==
      this.registration.confirmPassword
    ) {
      this.authError = 'Passwords do not match.';
      return;
    }

    const email = this.registration.email.trim().toLowerCase();
    this.loading = true;

    this.http.post<any>(
      `${this.API}/auth/register`,
      {
        name: this.registration.name.trim(),
        email,
        password: this.registration.password
      }
    ).subscribe({
      next: () => {
        this.registrationEmail = email;
        this.registration.password = '';
        this.registration.confirmPassword = '';
        this.verificationOtp = '';
        this.paymentReceipt = null;
        this.paymentMethod = 'UPI';

        this.changeAuthView('verify');
        this.authNotice =
          'Registration successful. Check your email for the OTP.';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err => this.authFailure(err, 'Registration failed.')
    });
  }

  // ============================================
  // VERIFY EMAIL OTP
  // ============================================

  verifyRegistrationOtp(): void {
    this.authError = '';
    this.authNotice = '';

    if (!/^\d{6}$/.test(this.verificationOtp.trim())) {
      this.authError = 'Enter a valid 6-digit OTP.';
      return;
    }

    this.loading = true;

    this.http.post<any>(
      `${this.API}/auth/verify-email`,
      {
        email: this.registrationEmail,
        otp: this.verificationOtp.trim()
      }
    ).subscribe({
      next: () => {
        this.verificationOtp = '';
        this.changeAuthView('payment');
        this.authNotice =
          'Email verified! Complete demo payment to activate your account.';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err =>
        this.authFailure(err, 'OTP verification failed.')
    });
  }

  // ============================================
  // RESEND OTP
  // ============================================

  resendRegistrationOtp(): void {
    this.authError = '';
    this.authNotice = '';
    this.loading = true;

    this.http.post<any>(
      `${this.API}/auth/resend-otp`,
      { email: this.registrationEmail }
    ).subscribe({
      next: () => {
        this.authNotice =
          'If eligible, a new OTP has been sent. Check your inbox.';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err =>
        this.authFailure(err, 'Unable to resend OTP.')
    });
  }

  // ============================================
  // REGISTRATION PAYMENT
  // ============================================

  payRegistrationFee(): void {
    this.authError = '';
    this.authNotice = '';

    if (!this.registrationEmail) {
      this.authError = 'Registration email is missing.';
      return;
    }

    if (this.loading) return;

    const paymentLabels = {
      UPI: 'UPI',
      CARD: 'Debit / Credit Card',
      NET_BANKING: 'Net Banking'
    };

    const confirmed = confirm(
      `Confirm ₹100 demo registration payment?\n\n` +
      `Payment Method: ${paymentLabels[this.paymentMethod]}\n` +
      `Email: ${this.registrationEmail}\n\n` +
      `No real money will be collected.`
    );

    if (!confirmed) return;

    this.loading = true;

    this.http.post<PaymentReceipt>(
      `${this.API}/registration-payment/demo-pay`,
      {
        email: this.registrationEmail,
        payment_method: this.paymentMethod
      }
    ).subscribe({
      next: response => {
        this.paymentReceipt = {
          member_id: response.member_id,
          receipt_number: response.receipt_number,
          payment_id: response.payment_id,
          amount: response.amount,
          currency: response.currency,
          payment_method: response.payment_method,
          payment_status: response.payment_status,
          receipt_email_sent:
            response.receipt_email_sent === true
        };

        this.email = this.registrationEmail;
        this.changeAuthView('payment-success');
        this.authNotice = 'Membership activated successfully!';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err =>
        this.authFailure(err, 'Unable to complete demo payment.')
    });
  }

  goToLoginAfterPayment(): void {
    this.changeAuthView('login');
    this.authNotice =
      'Membership activated. Log in with your email and password.';
  }

  // ============================================
  // FORGOT PASSWORD
  // ============================================

  requestPasswordReset(): void {
    this.authError = '';
    this.authNotice = '';

    if (!this.resetEmail.trim()) {
      this.authError = 'Enter your registered email address.';
      return;
    }

    this.resetEmail = this.resetEmail.trim().toLowerCase();
    this.loading = true;

    this.http.post<any>(
      `${this.API}/auth/forgot-password`,
      { email: this.resetEmail }
    ).subscribe({
      next: () => {
        this.changeAuthView('reset');
        this.authNotice =
          'If this email is registered, a reset OTP has been sent.';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err =>
        this.authFailure(err, 'Unable to request password reset.')
    });
  }

  // ============================================
  // RESET PASSWORD
  // ============================================

  submitPasswordReset(): void {
    this.authError = '';
    this.authNotice = '';

    if (!/^\d{6}$/.test(this.resetOtp.trim())) {
      this.authError = 'Enter a valid 6-digit OTP.';
      return;
    }

    if (
      !this.newPassword ||
      this.newPassword !== this.confirmNewPassword
    ) {
      this.authError = 'Passwords do not match.';
      return;
    }

    this.loading = true;

    this.http.post<any>(
      `${this.API}/auth/reset-password`,
      {
        email: this.resetEmail,
        otp: this.resetOtp.trim(),
        new_password: this.newPassword
      }
    ).subscribe({
      next: () => {
        this.email = this.resetEmail;
        this.resetOtp = '';
        this.newPassword = '';
        this.confirmNewPassword = '';

        this.changeAuthView('login');
        this.authNotice =
          'Password reset successful. Please log in.';
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: err =>
        this.authFailure(err, 'Password reset failed.')
    });
  }

  // ============================================
  // LOGIN
  // ============================================

  login(): void {
    if (!this.email.trim() || !this.password) {
      this.message = 'Please enter your email and password.';
      return;
    }

    this.loading = true;
    this.message = '';
    this.authError = '';

    this.auth.login(
      this.email.trim(),
      this.password
    ).subscribe({
      next: () => {
        this.password = '';
        this.initializeSession();
      },
      error: err => {
        this.loading = false;
        this.message =
          this.errorText(err, 'Invalid email or password.');
        this.cdr.detectChanges();
      }
    });
  }

  private initializeSession(): void {
    this.http.get<any>(
      `${this.API}/auth/me`
    ).subscribe({
      next: user => {
        const role = String(user.role || '').toUpperCase();

        if (role !== 'MEMBER' && role !== 'LIBRARIAN') {
          this.logout();
          return;
        }

        this.role = role;
        this.token = 'authenticated';
        this.loading = false;
        this.restoringSession = false;
        this.message = '';
        this.authNotice = '';
        this.authError = '';

        if (role === 'LIBRARIAN') {
          this.page = 'approvals';
          this.loadCheckoutRequests();
        } else {
          this.page = 'books';
          this.loadMyCheckoutRequests();
        }

        this.loadBooks();
        this.startAutoRefresh();
        this.cdr.detectChanges();
      },
      error: () => {
        this.auth.logout().subscribe({
          next: () => this.finishLogout(),
          error: () => this.finishLogout()
        });
      }
    });
  }

  // ============================================
  // LOGOUT
  // ============================================

  logout(): void {
    this.stopAutoRefresh();

    this.auth.logout().subscribe({
      next: () => this.finishLogout(),
      error: () => this.finishLogout()
    });
  }

  private finishLogout(): void {
    this.resetInterface();
    this.cdr.detectChanges();
  }

  private resetInterface(): void {
    this.stopAutoRefresh();

    this.token = '';
    this.role = '';
    this.page = 'books';
    this.email = '';
    this.password = '';
    this.search = '';
    this.message = '';

    this.authView = 'login';
    this.authNotice = '';
    this.authError = '';
    this.loading = false;
    this.restoringSession = false;

    this.books = [];
    this.dashboard = null;
    this.reservations = [];
    this.fines = [];
    this.checkoutRequests = [];
    this.myCheckoutRequests = [];

    this.editingBookId = '';
    this.copiesBookId = '';
    this.paymentReceipt = null;
    this.paymentMethod = 'UPI';
  }

  // ============================================
  // AUTO REFRESH
  // ============================================

  private startAutoRefresh(): void {
    this.stopAutoRefresh();

    this.refreshTimer = setInterval(() => {
      if (!this.token) return;

      this.loadBooks(true);

      if (
        this.role === 'LIBRARIAN' &&
        this.page === 'approvals'
      ) {
        this.loadCheckoutRequests(true);
      }

      if (this.role === 'MEMBER') {
        if (this.page === 'my-requests') {
          this.loadMyCheckoutRequests(true);
        }

        if (this.page === 'reservations') {
          this.loadReservations(true);
        }

        if (this.page === 'fines') {
          this.loadFines(true);
        }
      }
    }, 15000);
  }

  private stopAutoRefresh(): void {
    if (this.refreshTimer !== null) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  // ============================================
  // NAVIGATION
  // ============================================

  navigate(page: string): void {
    const librarianPages = [
      'approvals', 'books', 'manage-books'
    ];

    const memberPages = [
      'books', 'dashboard', 'my-requests',
      'reservations', 'fines'
    ];

    if (
      this.role === 'LIBRARIAN' &&
      !librarianPages.includes(page)
    ) return;

    if (
      this.role === 'MEMBER' &&
      !memberPages.includes(page)
    ) return;

    this.page = page;
    this.message = '';

    switch (page) {
      case 'books':
      case 'manage-books':
        this.loadBooks();
        break;

      case 'dashboard':
        this.loadDashboard();
        break;

      case 'my-requests':
        this.loadMyCheckoutRequests();
        break;

      case 'approvals':
        this.loadCheckoutRequests();
        break;

      case 'reservations':
        this.loadReservations();
        break;

      case 'fines':
        this.loadFines();
        break;
    }

    this.cdr.detectChanges();
  }

  // ============================================
  // BOOK CATALOGUE
  // ============================================

  loadBooks(silent = false): void {
    this.http.get<any[]>(
      `${this.API}/books/availability`
    ).subscribe({
      next: data => {
        this.books = data;
        this.cdr.detectChanges();
      },
      error: err => {
        if (!silent) {
          this.message =
            this.errorText(err, 'Unable to load books.');
          this.cdr.detectChanges();
        }
      }
    });
  }

  filteredBooks(): any[] {
    const query = this.search.trim().toLowerCase();

    if (!query) return this.books;

    return this.books.filter(book =>
      String(book.title || '')
        .toLowerCase().includes(query) ||
      String(book.author || '')
        .toLowerCase().includes(query)
    );
  }

  // ============================================
  // MEMBER: REQUEST BOOK
  // ============================================

  checkout(bookId: string): void {
    if (this.role !== 'MEMBER') return;

    const book = this.books.find(item => item.id === bookId);

    if (book && Number(book.available_copies) <= 0) {
      alert('No available copies. Please reserve this book.');
      return;
    }

    this.http.post<any>(
      `${this.API}/loans/checkout`,
      { book_id: bookId }
    ).subscribe({
      next: response => {
        alert(
          response.message ||
          'Checkout request submitted for librarian approval.'
        );
        this.loadMyCheckoutRequests();
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Checkout request failed.'));
        this.loadBooks();
      }
    });
  }

  // ============================================
  // MEMBER: MY REQUESTS
  // ============================================

  loadMyCheckoutRequests(silent = false): void {
    this.http.get<any[]>(
      `${this.API}/loans/requests/me`
    ).subscribe({
      next: data => {
        this.myCheckoutRequests = data;
        this.cdr.detectChanges();
      },
      error: err => {
        if (!silent) {
          this.message =
            this.errorText(err, 'Unable to load requests.');
          this.cdr.detectChanges();
        }
      }
    });
  }

  // ============================================
  // MEMBER: CANCEL PENDING REQUEST
  // ============================================

  cancelRequest(requestId: string): void {
    if (this.role !== 'MEMBER') return;

    const request = this.myCheckoutRequests.find(
      item => item.id === requestId
    );

    if (!request || request.status !== 'PENDING') {
      alert('Only pending requests can be cancelled.');
      return;
    }

    if (!confirm('Are you sure you want to cancel this request?')) {
      return;
    }

    this.http.post<any>(
      `${this.API}/loans/requests/${requestId}/cancel`,
      {}
    ).subscribe({
      next: response => {
        alert(
          response.message ||
          'Request cancelled successfully.'
        );

        this.loadMyCheckoutRequests();
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Unable to cancel request.'));
        this.loadMyCheckoutRequests();
      }
    });
  }

  // ============================================
  // LIBRARIAN: LOAD APPROVAL REQUESTS
  // ============================================

  loadCheckoutRequests(silent = false): void {
    this.http.get<any[]>(
      `${this.API}/loans/requests`
    ).subscribe({
      next: data => {
        this.checkoutRequests = data;
        this.cdr.detectChanges();
      },
      error: err => {
        if (!silent) {
          this.message =
            this.errorText(err, 'Unable to load approvals.');
          this.cdr.detectChanges();
        }
      }
    });
  }

  // ============================================
  // LIBRARIAN: APPROVE
  // ============================================

  approveRequest(requestId: string): void {
    if (this.role !== 'LIBRARIAN') return;

    this.http.post<any>(
      `${this.API}/loans/requests/${requestId}/approve`,
      {}
    ).subscribe({
      next: response => {
        alert(
          response.message ||
          'Checkout approved successfully!'
        );

        this.loadCheckoutRequests();
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Approval failed.'));
        this.loadCheckoutRequests();
      }
    });
  }

  // ============================================
  // LIBRARIAN: REJECT
  // ============================================

  rejectRequest(requestId: string): void {
    if (this.role !== 'LIBRARIAN') return;

    this.http.post<any>(
      `${this.API}/loans/requests/${requestId}/reject`,
      {}
    ).subscribe({
      next: response => {
        alert(response.message || 'Request rejected.');
        this.loadCheckoutRequests();
      },
      error: err => {
        alert(this.errorText(err, 'Rejection failed.'));
        this.loadCheckoutRequests();
      }
    });
  }

  // ============================================
  // MEMBER DASHBOARD
  // ============================================

  loadDashboard(): void {
    this.http.get<any>(
      `${this.API}/dashboard/me`
    ).subscribe({
      next: data => {
        this.dashboard = data;
        this.cdr.detectChanges();
      },
      error: err => {
        this.message =
          this.errorText(err, 'Unable to load dashboard.');
        this.cdr.detectChanges();
      }
    });
  }

  // ============================================
  // RETURN BOOK
  // ============================================

  returnBook(loanId: string): void {
    if (this.role !== 'MEMBER') return;

    this.http.post<any>(
      `${this.API}/loans/${loanId}/return`,
      {}
    ).subscribe({
      next: () => {
        alert('Book returned successfully!');
        this.loadDashboard();
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Return failed.'));
      }
    });
  }

  // ============================================
  // MEMBER RESERVATIONS
  // ============================================

  loadReservations(silent = false): void {
    this.http.get<any[]>(
      `${this.API}/reservations/me`
    ).subscribe({
      next: data => {
        this.reservations = data;
        this.cdr.detectChanges();
      },
      error: err => {
        if (!silent) {
          this.message =
            this.errorText(err, 'Unable to load reservations.');
          this.cdr.detectChanges();
        }
      }
    });
  }

  reserveBook(bookId: string): void {
    if (this.role !== 'MEMBER') return;

    this.http.post<any>(
      `${this.API}/reservations`,
      { book_id: bookId }
    ).subscribe({
      next: reservation => {
        this.http.get<any>(
          `${this.API}/reservations/${reservation.id}/position`
        ).subscribe({
          next: queue => {
            if (queue.queue_position != null) {
              alert(
                `Reservation successful!\n\n` +
                `Your queue position: ${queue.queue_position}\n` +
                `Members ahead: ${queue.members_ahead}`
              );
            } else {
              alert(
                `Reservation successful!\n` +
                `Status: ${queue.status}`
              );
            }

            this.loadReservations();
            this.loadBooks();
          },
          error: () => {
            alert('Reservation created successfully!');
            this.loadReservations();
            this.loadBooks();
          }
        });
      },
      error: err => {
        alert(this.errorText(err, 'Reservation failed.'));
      }
    });
  }

  // ============================================
  // RESERVATION QUEUE POSITION
  // ============================================

  viewQueuePosition(reservationId: string): void {
    this.http.get<any>(
      `${this.API}/reservations/${reservationId}/position`
    ).subscribe({
      next: queue => {
        if (queue.queue_position != null) {
          alert(
            `Your queue position: ${queue.queue_position}\n` +
            `Members ahead: ${queue.members_ahead}`
          );
        } else {
          alert(
            queue.message ||
            `Status: ${queue.status}`
          );
        }
      },
      error: err => {
        alert(
          this.errorText(err, 'Unable to get queue position.')
        );
      }
    });
  }

  // ============================================
  // CANCEL RESERVATION
  // ============================================

  cancelReservation(reservationId: string): void {
    if (this.role !== 'MEMBER') return;

    this.http.delete<any>(
      `${this.API}/reservations/${reservationId}`
    ).subscribe({
      next: () => {
        alert('Reservation cancelled.');
        this.loadReservations();
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Cancellation failed.'));
      }
    });
  }

  // ============================================
  // FINES
  // ============================================

  loadFines(silent = false): void {
    this.http.get<any[]>(
      `${this.API}/fines/me`
    ).subscribe({
      next: data => {
        this.fines = data;
        this.cdr.detectChanges();
      },
      error: err => {
        if (!silent) {
          this.message =
            this.errorText(err, 'Unable to load fines.');
          this.cdr.detectChanges();
        }
      }
    });
  }

  // ============================================
  // DEMO FINE PAYMENT
  // ============================================

  demoPayFine(fineId: string): void {
    if (this.role !== 'MEMBER') return;

    const confirmed = confirm(
      'This is a DEMO payment.\n' +
      'No real money will be collected.\n\n' +
      'Mark this outstanding fine as paid?'
    );

    if (!confirmed) return;

    this.http.post<any>(
      `${this.API}/fines/${fineId}/demo-pay`,
      {}
    ).subscribe({
      next: response => {
        alert(
          `Demo payment successful!\n\n` +
          `Amount: ₹${response.amount}\n` +
          `Status: ${response.status}\n` +
          `No real money was collected.`
        );

        this.loadFines();

        if (this.page === 'dashboard') {
          this.loadDashboard();
        }
      },
      error: err => {
        alert(this.errorText(err, 'Demo payment failed.'));
        this.loadFines();
      }
    });
  }

  // ============================================
  // LIBRARIAN: ADD BOOK
  // ============================================

  addBook(): void {
    if (this.role !== 'LIBRARIAN') return;

    if (
      !this.newBook.title.trim() ||
      !this.newBook.author.trim() ||
      !Number.isInteger(this.newBook.total_copies) ||
      this.newBook.total_copies < 1
    ) {
      alert('Enter valid book details.');
      return;
    }

    this.http.post<any>(
      `${this.API}/books`,
      this.newBook
    ).subscribe({
      next: () => {
        alert('Book added successfully!');

        this.newBook = {
          title: '',
          author: '',
          total_copies: 1
        };

        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Unable to add book.'));
      }
    });
  }

  // ============================================
  // LIBRARIAN: EDIT BOOK
  // ============================================

  startEditBook(book: any): void {
    this.editingBookId = book.id;

    this.editBook = {
      title: book.title,
      author: book.author
    };

    this.cdr.detectChanges();
  }

  cancelEditBook(): void {
    this.editingBookId = '';
  }

  saveBook(): void {
    if (!this.editingBookId) return;

    if (
      !this.editBook.title.trim() ||
      !this.editBook.author.trim()
    ) {
      alert('Enter a valid title and author.');
      return;
    }

    this.http.put<any>(
      `${this.API}/books/${this.editingBookId}`,
      this.editBook
    ).subscribe({
      next: () => {
        alert('Book updated successfully!');
        this.editingBookId = '';
        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Unable to update book.'));
      }
    });
  }

  // ============================================
  // LIBRARIAN: ADD COPIES
  // ============================================

  startAddCopies(bookId: string): void {
    this.copiesBookId = bookId;
    this.copiesQuantity = 1;
    this.cdr.detectChanges();
  }

  cancelAddCopies(): void {
    this.copiesBookId = '';
  }

  addCopies(): void {
    if (
      !this.copiesBookId ||
      !Number.isInteger(this.copiesQuantity) ||
      this.copiesQuantity < 1
    ) {
      alert('Enter a valid number of copies.');
      return;
    }

    this.http.post<any>(
      `${this.API}/books/${this.copiesBookId}/copies`,
      { quantity: this.copiesQuantity }
    ).subscribe({
      next: () => {
        alert('Book copies added successfully!');

        this.copiesBookId = '';
        this.copiesQuantity = 1;

        this.loadBooks();
      },
      error: err => {
        alert(this.errorText(err, 'Unable to add copies.'));
      }
    });
  }

  // ============================================
  // UNIQUE FALLBACK COVER
  // ============================================

  private makeBookCover(book: any): string {
    const title = String(book?.title || 'Untitled Book');
    const author = String(book?.author || 'Unknown Author');

    const palettes = [
      ['#203b58', '#5b91a8'],
      ['#5c294b', '#bf7894'],
      ['#744127', '#d59b57'],
      ['#264f42', '#8ab39c'],
      ['#403b74', '#a49ed0'],
      ['#733e37', '#db947f'],
      ['#31516a', '#a5c6db'],
      ['#634c25', '#d3b477']
    ];

    const hash = [...title].reduce(
      (total, char) => total + char.charCodeAt(0),
      0
    );

    const [dark, light] = palettes[hash % palettes.length];

    const escapeXml = (value: string): string =>
      value.replace(/[&<>"']/g, char => {
        const entities: Record<string, string> = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&apos;'
        };

        return entities[char];
      });

    const words = title.split(/\s+/);
    const lines: string[] = [];
    let current = '';

    for (const word of words) {
      if (
        (current + ' ' + word).trim().length > 17 &&
        current
      ) {
        lines.push(current);
        current = word;
      } else {
        current = `${current} ${word}`.trim();
      }
    }

    if (current) lines.push(current);

    const titleSvg = lines.slice(0, 5).map(
      (line, index) => `
        <text x="120" y="${132 + index * 28}"
          text-anchor="middle"
          font-family="Arial, sans-serif"
          font-size="18"
          font-weight="bold"
          fill="#ffffff">
          ${escapeXml(line)}
        </text>
      `
    ).join('');

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg"
           width="240" height="340"
           viewBox="0 0 240 340">
        <defs>
          <linearGradient id="background"
            x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="${dark}"/>
            <stop offset="100%" stop-color="${light}"/>
          </linearGradient>
        </defs>

        <rect width="240" height="340"
          fill="url(#background)"/>

        <rect x="13" y="13" width="214" height="314"
          fill="none" stroke="#ffffff"
          stroke-opacity="0.45" stroke-width="2"/>

        <circle cx="120" cy="76" r="28"
          fill="none" stroke="#ffffff"
          stroke-opacity="0.65" stroke-width="2"/>

        <path d="M102 68 Q111 64 120 70
          Q129 64 138 68 V86
          Q129 82 120 88
          Q111 82 102 86 Z"
          fill="none" stroke="#ffffff"
          stroke-width="2"/>

        ${titleSvg}

        <line x1="65" y1="275" x2="175" y2="275"
          stroke="#ffffff" stroke-opacity="0.65"/>

        <text x="120" y="298"
          text-anchor="middle"
          font-family="Arial, sans-serif"
          font-size="12" fill="#ffffff">
          ${escapeXml(author.slice(0, 30))}
        </text>
      </svg>
    `;

    return 'data:image/svg+xml;charset=UTF-8,' +
      encodeURIComponent(svg);
  }

  // ============================================
  // BOOK COVER LOOKUP
  // REAL COVER FIRST, CUSTOM FALLBACK SECOND
  // ============================================

  bookCoverUrl(book: any): string {
    const title = String(book?.title || '').trim();
    const author = String(book?.author || '').trim();

    if (!title) {
      return this.makeBookCover(book);
    }

    const key =
      `${title.toLowerCase()}|${author.toLowerCase()}`;

    const cached = this.bookCoverCache.get(key);

    if (cached) return cached;

    // Try the same direct cover URL that previously
    // displayed actual covers in the catalogue.
    const directCover =
      'https://covers.openlibrary.org/b/title/' +
      encodeURIComponent(title) +
      '-M.jpg?default=false';

    this.bookCoverCache.set(key, directCover);

    return directCover;
  }

  // ============================================
  // IMAGE ERROR: SEARCH OPEN LIBRARY
  // ============================================

  onBookCoverError(event: Event): void {
    const image = event.target as HTMLImageElement;

    if (!image) return;

    const title = image.alt.replace(/^Cover of /, '');

    const book = this.books.find(
      item => String(item.title) === title
    ) || { title, author: '' };

    const author = String(book.author || '').trim();

    const key =
      `${title.toLowerCase()}|${author.toLowerCase()}`;

    const fallback = this.makeBookCover(book);

    // If the fallback itself fails, stop retrying.
    if (image.src.startsWith('data:image/svg+xml')) {
      return;
    }

    // If lookup has already been attempted,
    // use the custom fallback immediately.
    if (this.bookCoverLoading.has(key)) {
      image.src = fallback;
      return;
    }

    this.bookCoverLoading.add(key);

    const params = new URLSearchParams({
      title,
      author,
      limit: '10',
      fields: 'title,author_name,cover_i'
    });

    this.http.get<any>(
      `https://openlibrary.org/search.json?${params.toString()}`
    ).subscribe({
      next: result => {
        const docs: any[] =
          Array.isArray(result?.docs)
            ? result.docs
            : [];

        const normalize = (value: string): string =>
          value.toLowerCase().replace(/[^a-z0-9]/g, '');

        const normalizedTitle = normalize(title);
        const normalizedAuthor = normalize(author);

        const matchingBooks = docs.filter(
          (item: any) =>
            normalize(String(item.title || '')) ===
              normalizedTitle &&
            Number(item.cover_i) > 0
        );

        const authorMatch = matchingBooks.find(
          (item: any) =>
            (item.author_name || []).some(
              (name: string) =>
                normalize(name) === normalizedAuthor
            )
        );

        const match =
          authorMatch ||
          (matchingBooks.length === 1
            ? matchingBooks[0]
            : null);

        if (match) {
          const actualCover =
            `https://covers.openlibrary.org/b/id/${match.cover_i}-M.jpg`;

          this.bookCoverCache.set(key, actualCover);

          image.src = actualCover;
        } else {
          this.bookCoverCache.set(key, fallback);
          image.src = fallback;
        }

        this.cdr.detectChanges();
      },
      error: () => {
        this.bookCoverCache.set(key, fallback);
        image.src = fallback;
        this.cdr.detectChanges();
      }
    });
  }
}
