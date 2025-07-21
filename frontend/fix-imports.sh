#!/bin/bash

# Fix imports in all TypeScript files
cd src

# Replace @/components imports
find . -name "*.tsx" -o -name "*.ts" | xargs sed -i "s|from '@/components/|from '../components/|g"

# Replace @/services imports  
find . -name "*.tsx" -o -name "*.ts" | xargs sed -i "s|from '@/services/|from '../services/|g"

# Replace @/contexts imports
find . -name "*.tsx" -o -name "*.ts" | xargs sed -i "s|from '@/contexts/|from '../contexts/|g"

# Replace @/pages imports
find . -name "*.tsx" -o -name "*.ts" | xargs sed -i "s|from '@/pages/|from '../pages/|g"

echo "✅ Fixed all @ imports to use relative paths"