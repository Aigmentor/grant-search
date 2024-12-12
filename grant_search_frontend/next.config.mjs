/** @type {import('next').NextConfig} */

const dev = process.env.NODE_ENV !== 'production';

const devConfig = {
    // output: 'export',
    // basePath: '/static',
    async rewrites() {
		return [
			{
				source: '/app/:path*',
				destination: 'http://127.0.0.1:5000/app/:path*',
			},
			{
				source: '/api/:path*',
				destination: 'http://127.0.0.1:5000/api/:path*',
			},
			{
				source: '/auth/:path*',
				destination: 'http://127.0.0.1:5000/auth/:path*',
			},
			{
				source: '/static/:path*',
				destination: 'http://127.0.0.1:5000/static/:path*',
			},
		]
	},
};

const productionConfig = {
    output: 'export',
    basePath: '/static',
}

const nextConfig = dev ? devConfig : productionConfig;
export default nextConfig;
