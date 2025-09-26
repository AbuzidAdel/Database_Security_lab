# Database Security Lab - Serverless Learning Platform

A modern, serverless web application for interactive database security learning, built with FastAPI and deployed on AWS Lambda.

## 🚀 Features

### Core Functionality
- **Interactive Learning Platform**: Browse exercises and step-by-step tutorials
- **Modern Web Interface**: Responsive design with Bootstrap 5
- **Serverless Architecture**: Runs on AWS Lambda for scalability and cost-effectiveness
- **Content Management**: Rich text editor for creating and editing content

### Authentication & Authorization
- **JWT-based Authentication**: Secure user login and session management
- **Role-based Access Control**: Admin and regular user roles
- **User Registration**: Self-service user registration

### Content Management
- **Exercise Management**: Create, edit, and organize learning exercises
- **Step-by-Step Tutorials**: Detailed steps with rich content support
- **Hidden Content**: Control visibility of content for different user types
- **Rich Text Editing**: Quill.js editor with support for:
  - Text formatting (bold, italic, underline)
  - Code blocks and syntax highlighting
  - Lists and indentation
  - Links and images
  - Mathematical expressions

### Admin Features
- **Admin Dashboard**: Comprehensive content management interface
- **Content Statistics**: Overview of exercises, steps, and hidden content
- **Bulk Operations**: Import/export content functionality
- **User Management**: Admin user creation and management

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI with Mangum for AWS Lambda compatibility
- **Frontend**: HTML5, Bootstrap 5, JavaScript (ES6+)
- **Database**: Amazon DynamoDB for scalable NoSQL storage
- **File Storage**: Amazon S3 for static assets and uploads
- **CDN**: Amazon CloudFront for global content delivery
- **Authentication**: JWT tokens with bcrypt password hashing

### AWS Services Used
- **AWS Lambda**: Serverless compute for the application
- **API Gateway**: RESTful API management and routing
- **DynamoDB**: NoSQL database for users and content
- **S3**: Object storage for static assets and file uploads
- **CloudFront**: Content delivery network for performance
- **CloudFormation**: Infrastructure as Code via SAM templates

## 📦 Installation & Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.9 or higher
- Node.js (for frontend dependencies, optional)

### Quick Deployment

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Database_Security_lab
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy to AWS**:
   ```bash
   ./deploy.sh
   ```

   The deployment script will:
   - Build and deploy the SAM application
   - Create all necessary AWS resources
   - Set up an admin user
   - Migrate existing content

### Manual Deployment

1. **Build the application**:
   ```bash
   sam build
   ```

2. **Deploy with custom parameters**:
   ```bash
   sam deploy \
     --stack-name database-security-lab \
     --capabilities CAPABILITY_IAM \
     --parameter-overrides SecretKey="your-secret-key"
   ```

3. **Create admin user**:
   ```bash
   python3 -c "
   import boto3
   from passlib.context import CryptContext
   
   # Create admin user in DynamoDB
   # (See deploy.sh for complete example)
   "
   ```

4. **Migrate content**:
   ```bash
   export CONTENT_TABLE=your-content-table-name
   python3 migrate_content.py
   ```

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: JWT secret key for token generation
- `USERS_TABLE`: DynamoDB table name for users
- `CONTENT_TABLE`: DynamoDB table name for content
- `S3_BUCKET`: S3 bucket name for file uploads
- `AWS_REGION`: AWS region for all services

### SAM Template Parameters
- `SecretKey`: Secret key for JWT tokens (required)

## 📚 Usage

### For Learners
1. **Browse Exercises**: Visit the home page to see available exercises
2. **Follow Steps**: Click on exercises to see detailed step-by-step instructions
3. **Interactive Content**: Engage with rich content including code examples and images

### For Administrators
1. **Access Admin Panel**: Login and navigate to `/admin`
2. **Create Content**: Use the rich text editor to create new exercises and steps
3. **Manage Visibility**: Control which content is visible to regular users
4. **Import Legacy Content**: Use the migration tools to import existing HTML content

### Content Structure
- **Exercises**: Top-level learning modules (e.g., "MySQL Installation")
- **Steps**: Individual instructions within exercises (e.g., "Download MySQL")
- **References**: Additional resources and links

## 🔒 Security Features

### Authentication
- JWT tokens with configurable expiration
- Bcrypt password hashing with salt
- Secure session management

### Authorization
- Role-based access control (admin/user)
- Protected admin routes
- Content visibility controls

### Data Protection
- Input validation and sanitization
- SQL injection prevention (NoSQL database)
- XSS protection in content rendering
- CORS configuration for API security

## 🛠️ Development

### Local Development
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export SECRET_KEY="development-secret-key"
   export USERS_TABLE="local-users-table"
   export CONTENT_TABLE="local-content-table"
   ```

3. **Run locally**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   - Open http://localhost:8000
   - API documentation: http://localhost:8000/docs

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=app tests/
```

### Code Structure
```
Database_Security_lab/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── template.yaml         # SAM CloudFormation template
├── deploy.sh             # Deployment script
├── migrate_content.py    # Content migration script
├── templates/            # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── exercise.html
│   ├── step.html
│   ├── error.html
│   └── admin/
│       └── dashboard.html
├── static/              # Static assets (CSS, JS, images)
└── tests/               # Test files
```

## 📊 Monitoring & Maintenance

### CloudWatch Metrics
- Lambda function invocations and duration
- API Gateway request counts and latency
- DynamoDB read/write capacity and throttling
- CloudFront cache hit rates

### Logging
- Application logs in CloudWatch Logs
- Structured logging with correlation IDs
- Error tracking and alerting

### Backup & Recovery
- DynamoDB point-in-time recovery enabled
- S3 versioning for uploaded files
- CloudFormation stack for infrastructure recovery

## 🔄 Migration from Legacy System

The application includes tools to migrate from the existing HTML-based system:

### Migration Process
1. **Parse HTML Files**: Extract content from existing HTML files
2. **Structure Conversion**: Convert frame-based navigation to modern structure
3. **Content Import**: Import exercises, steps, and references to DynamoDB
4. **Asset Migration**: Move images and files to S3

### Migration Script Usage
```bash
# Migrate all content
python3 migrate_content.py

# Migrate specific directory
python3 migrate_content.py --html-dir /path/to/html/files

# Export to JSON only (no database)
python3 migrate_content.py --no-db

# Custom AWS region
python3 migrate_content.py --aws-region eu-west-1
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code style
- Use type hints for function parameters and return values
- Write unit tests for new functionality
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Q: Deployment fails with permission errors**
A: Ensure your AWS CLI is configured with appropriate IAM permissions for Lambda, DynamoDB, S3, and CloudFormation.

**Q: Content migration fails**
A: Check that the CONTENT_TABLE environment variable is set correctly and the table exists.

**Q: Admin user creation fails**
A: Verify that the USERS_TABLE exists and you have DynamoDB write permissions.

### Getting Help
- Check the [Issues](https://github.com/your-repo/issues) page for known problems
- Create a new issue with detailed error messages and steps to reproduce
- Contact the development team for urgent issues

## 🔮 Future Enhancements

- **Multi-language Support**: Internationalization for global users
- **Advanced Analytics**: Learning progress tracking and analytics
- **Mobile App**: Native mobile applications for iOS and Android
- **Collaborative Features**: User comments and discussion forums
- **Integration APIs**: Connect with external learning management systems
- **Advanced Search**: Full-text search across all content
- **Offline Support**: Progressive Web App with offline capabilities

---

**Built with ❤️ for database security education**